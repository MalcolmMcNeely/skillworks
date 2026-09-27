using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // Cost is the only Measure this read answers.
    private const string TurnRead = "claude_code.api_request";

    // Tool calls and the tool half of Faults, and no part of Cost or Friction.
    private const string ToolResultRead = "claude_code.tool_result";

    // The read that finds the rows and the read that names them, and no Measure's.
    private const string PromptRead = "claude_code.user_prompt";

    [Fact]
    public async Task Draws_the_rows_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var lines = await studio.SessionLines(count: 2);

        Assert.Equal(["head", "sessions"], lines.Select(StudioHost.KindOf));
        Assert.Equal(["The run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events, TurnRead);
    }

    [Fact]
    public async Task Sends_a_measure_the_moment_its_read_lands_while_another_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")));

        var lines = await studio.SessionLines(count: 5);

        // Nothing ready waited on Cost, and no line was held back to buy a fixed order.
        Assert.Equal(["head", "sessions", "measure", "measure", "measure"], lines.Select(StudioHost.KindOf));
        Assert.Equal(
            ["faults", "friction", "toolCalls"],
            lines.Skip(2).Select(line => (string?)line["measure"]).Order(StringComparer.Ordinal));

        await StillOut(events, TurnRead);
    }

    [Fact]
    public async Task Draws_the_rows_narrowed_by_a_skill_while_a_measure_read_is_still_out()
    {
        using var events = Holding(TurnRead);
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run that swept"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The run that did not"));
        await studio.Push(new SkillActivated("comment-sweep", At(Yesterday, "09:05:00.000")) { Session = Morning });

        // The activation read decides which rows exist, so it lands with the reads that name them.
        var lines = await studio.SessionLines("?skill=comment-sweep", count: 2);

        Assert.Equal(["The run that swept"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        await StillOut(events, TurnRead);
    }

    [Fact]
    public async Task Reads_a_quiet_period_as_quiet_rather_than_as_a_store_that_fell_short()
    {
        using var studio = new StudioHost();

        var answer = await studio.SessionAnswer("?repository=acme/xi");

        // A period is judged on every run in it, whatever the Repository asked for.
        Assert.Empty(answer.Sessions);
        Assert.Equal("quiet", answer.Gap.Kind);
    }

    [Fact]
    public async Task Says_telemetry_is_off_for_an_empty_list_while_the_switch_is_off()
    {
        using var studio = new StudioHost(emitting: false);

        // An empty list with the switch off is explained by the switch, not by a quiet month.
        Assert.Equal("telemetryOff", (await studio.SessionAnswer()).Gap.Kind);
    }

    [Fact]
    public async Task Asks_the_events_store_for_nothing_twice()
    {
        // Breaks no read, so every route is recorded.
        using var events = BrokenEventsStore.DownOn(_ => false);
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "09:05:00.000"), "The build step") with { Parent = Morning });

        await studio.SessionAnswer();

        // A gate that asked again for what a Measure had already asked for would cost a reader a whole round.
        Assert.Equal(events.Asked.Distinct(), events.Asked);
    }

    [Fact]
    public async Task Empties_the_table_when_one_gate_read_fell_short()
    {
        using var events = Breaking(PromptRead);
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer();

        // A run this read leaves unnamed is a row Studio cannot vouch for, so one short is none.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Fact]
    public async Task Empties_the_table_when_the_read_that_names_the_rows_fell_short()
    {
        // Only the read that names the loaded rows asks for their Prompts by Session.
        using var events = BrokenEventsStore.DownOn(asked =>
            asked.Contains(PromptRead, StringComparison.Ordinal) && asked.Contains("session_id=~", StringComparison.Ordinal));
        using var studio = new StudioHost(events: events);

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer();

        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    private static BrokenEventsStore Holding(string read) =>
        BrokenEventsStore.StallingOn(asked => asked.Contains(read, StringComparison.Ordinal));

    private static BrokenEventsStore Breaking(string read) =>
        BrokenEventsStore.DownOn(asked => asked.Contains(read, StringComparison.Ordinal));

    // Without this a predicate that matched no read would leave every test above passing on an answer it never held.
    private static async Task StillOut(BrokenEventsStore events, string read) =>
        Assert.Contains(read, await events.HeldRead, StringComparison.Ordinal);
}
