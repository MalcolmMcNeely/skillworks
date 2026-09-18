using Skillworks.Core.EventsStore;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // Cost is the only Measure this read answers.
    private const string TurnRead = "claude_code.api_request";

    // Tool calls and the tool half of Faults, and no part of Cost or Friction.
    private const string ToolResultRead = "claude_code.tool_result";

    // The one read grouped by nothing, so no other read of the answer is spelled this way.
    private const string SurveyRead = "sum (count_over_time";

    // One of the five that name a run, and no Measure's.
    private const string PromptRead = "claude_code.user_prompt";

    [Fact]
    public async Task Draws_the_rows_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var lines = await studio.SessionLines(count: 2);

        Assert.Equal(["head", "sessions"], lines.Select(StudioHost.KindOf));
        Assert.Equal(["The run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events);
    }

    [Fact]
    public async Task Sends_a_measure_the_moment_its_read_lands_while_another_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")));

        var lines = await studio.SessionLines(count: 5);

        // Nothing ready waited on Cost, and no line was held back to buy a fixed order.
        Assert.Equal(["head", "sessions", "measure", "measure", "measure"], lines.Select(StudioHost.KindOf));
        Assert.Equal(
            ["faults", "friction", "toolCalls"],
            lines.Skip(2).Select(line => (string?)line["measure"]).Order(StringComparer.Ordinal));

        await StillOut(events);
    }

    [Fact]
    public async Task Draws_the_rows_sorted_on_a_column_that_is_no_measure_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The early run"),
            new SessionEvent(Morning, "assistant_response", At(Yesterday, "09:10:00.000")),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The later run"),
            new SessionEvent(Afternoon, "assistant_response", At(Yesterday, "14:30:00.000")));

        // Length is read from the first and last event, which the gate already holds.
        var lines = await studio.SessionLines("?sort=length", count: 2);

        Assert.Equal(["The later run", "The early run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events);
    }

    [Theory]
    [InlineData("cost", ToolResultRead)]
    [InlineData("toolCalls", TurnRead)]
    [InlineData("faults", TurnRead)]
    public async Task Draws_the_rows_sorted_on_a_measure_while_another_measures_read_is_still_out(
        string sort,
        string held)
    {
        using var events = Holding(held);
        using var studio = new StudioHost(events: events);

        await ThreeRuns(studio);

        // Only a gate that waited for this Measure can put the rows in order while another read is out.
        var lines = await studio.SessionLines($"?sort={sort}", count: 2);

        Assert.Equal(["Beta run", "Gamma run", "Alpha run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events);
    }

    [Fact]
    public async Task Draws_the_rows_narrowed_by_a_skill_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run that swept"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The run that did not"));
        await studio.Push(new SkillActivated("comment-sweep", At(Yesterday, "09:05:00.000")) { Session = Morning });

        // The activation read decides which rows exist, so it lands with the five that name them.
        var lines = await studio.SessionLines("?skill=comment-sweep", count: 2);

        Assert.Equal(["The run that swept"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events);
    }

    [Fact]
    public async Task Draws_the_rows_narrowed_by_a_repository_while_the_survey_is_still_out()
    {
        // A Repository narrows every other read in the store, so the one that names no repository is the survey.
        using var events = BrokenEventsStore.StallingOn(read => !read.Contains("acme", StringComparison.Ordinal));
        using var studio = new StudioHost(events: events);

        await studio.Push(
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The chosen run", "acme/xi"),
            Ran(Afternoon, At(Yesterday, "14:00:00.000"), "The other run", "acme/nu"));

        // The survey only tells a quiet period from a narrowed one, which the end line reports.
        var lines = await studio.SessionLines("?repository=acme/xi", count: 2);

        Assert.Equal(["The chosen run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events);
    }

    [Fact]
    public async Task Draws_the_rows_once_in_the_order_of_the_measure_a_reader_sorted_on()
    {
        using var studio = new StudioHost();

        await ThreeRuns(studio);

        var lines = await studio.SessionLines("?sort=cost");
        var kinds = lines.Select(StudioHost.KindOf).ToList();

        // Drawn once and ahead of every Measure, so the table never settles into a second order.
        Assert.Single(kinds, kind => kind == "sessions");
        Assert.True(kinds.IndexOf("sessions") < kinds.IndexOf("measure"));
        Assert.Equal(["Beta run", "Gamma run", "Alpha run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));
    }

    [Fact]
    public async Task Reads_a_quiet_period_as_quiet_rather_than_as_a_store_that_fell_short()
    {
        using var studio = new StudioHost();

        var answer = await studio.SessionAnswer("?repository=acme/xi");

        // The survey left the gate, and it is the read a quiet period is judged on.
        Assert.Empty(answer.Sessions);
        Assert.Equal("quiet", answer.Gap.Kind);
    }

    [Fact]
    public async Task Asks_the_events_store_for_nothing_twice()
    {
        // Down only before the two days the lookback covers, so nothing here breaks and every route is recorded.
        using var events = BrokenEventsStore.DownBefore(Yesterday);
        using var studio = new StudioHost(events: events, lookbackDays: 2);

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        await studio.SessionAnswer();

        // A gate that asked again for what a Measure had already asked for would cost a reader a whole round.
        Assert.Equal(events.Asked.Distinct(), events.Asked);
    }

    [Fact]
    public async Task Empties_the_table_when_one_gate_read_fell_short()
    {
        using var events = Breaking(PromptRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer();

        // A run this read leaves unnamed is a row Studio cannot vouch for, so one short is none.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Theory]
    [InlineData("cost", TurnRead)]
    [InlineData("toolCalls", ToolResultRead)]
    [InlineData("faults", ToolResultRead)]
    public async Task Empties_the_table_when_the_measure_a_reader_sorted_on_fell_short(string sort, string broken)
    {
        using var events = Breaking(broken);
        using var studio = new StudioHost(events: events);

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer($"?sort={sort}");

        // Rows drawn in an order this read never gave would settle again the moment it landed.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Fact]
    public async Task Draws_the_rows_when_the_survey_read_fell_short()
    {
        using var events = Breaking(SurveyRead);
        using var studio = new StudioHost(events: events);

        await studio.Push(Ran(Morning, At(Yesterday, "09:00:00.000"), "The run", "acme/xi"));

        var answer = await studio.SessionAnswer("?repository=acme/xi");

        // The survey tells a quiet period from a narrowed one, which a table with rows on it answers already.
        Assert.Equal(["The run"], answer.Sessions.Select(session => session.Name));
        Assert.Equal("complete", answer.Gap.Kind);
    }

    private static BrokenEventsStore Holding(string read) =>
        BrokenEventsStore.StallingOn(asked => asked.Contains(read, StringComparison.Ordinal));

    private static BrokenEventsStore Breaking(string read) =>
        BrokenEventsStore.DownOn(asked => asked.Contains(read, StringComparison.Ordinal));

    // Without this a predicate that matched no read would leave every test above passing on an answer it never held.
    private static async Task StillOut(BrokenEventsStore events) =>
        Assert.True(await events.HeldFor < TimeSpan.FromSeconds(new LokiOptions().TimeoutSeconds));
}
