using Skillworks.Core.Tests.TraceStore;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // A trace of its own for each run, as Claude Code never writes two runs into one.
    private const string MorningTrace = "7a1c0a9e0000400080000000000000b1";

    private const string EveningTrace = "7a1c0a9e0000400080000000000000b3";

    private const string MorningSpan = "c11c0a9e00000001";

    private const string EveningSpan = "c11c0a9e00000003";

    [Fact]
    public async Task Narrows_the_table_to_a_span_of_days_and_takes_both_ends_in()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-12T09:00:00.000Z", "The run before"),
            SessionEvent.Titled(Afternoon, "2026-09-13T09:00:00.000Z", "The first day"),
            SessionEvent.Titled(Evening, "2026-09-14T09:00:00.000Z", "The last day"));

        var names = (await studio.SessionsIn("?from=2026-09-13&to=2026-09-14")).Select(session => session.Name);

        Assert.Equal(["The last day", "The first day"], names);
    }

    [Fact]
    public async Task Counts_a_span_of_days_in_whole_utc_days()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-13T00:00:00.000Z", "The first instant"),
            SessionEvent.Titled(Afternoon, "2026-09-13T23:59:59.000Z", "The last instant"));

        // A local day would put a late run on another day and drop it from the answer.
        Assert.Equal(2, (await studio.SessionsIn("?from=2026-09-13&to=2026-09-13")).Count);
    }

    [Fact]
    public async Task Says_which_days_a_narrowed_table_covers_and_that_they_are_not_the_lookback()
    {
        using var studio = new StudioHost();

        var span = (await studio.SessionAnswer("?from=2026-09-13&to=2026-09-14")).Head.Span;

        Assert.False(span.Lookback);
        Assert.Equal(Day("2026-09-13"), span.From);
        Assert.Equal(Day("2026-09-14"), span.To);
    }

    [Fact]
    public async Task Narrows_the_table_to_one_repository()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The chosen run", "acme/xi"),
            Ran(Afternoon, "2026-09-14T14:00:00.000Z", "The other run", "acme/nu"));

        Assert.Equal(["The chosen run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Answers_with_no_runs_for_a_repository_that_is_a_near_miss()
    {
        using var studio = new StudioHost();

        await studio.Push(Ran(Morning, "2026-09-14T09:00:00.000Z", "The chosen run", "acme/xi"));

        Assert.Empty(await studio.SessionsIn("?repository=acme/x"));
    }

    [Fact]
    public async Task Leaves_a_run_that_names_no_repository_out_when_one_is_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The placed run", "acme/xi"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The run from nowhere"));

        Assert.Equal(["The placed run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_repository_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        SessionEvent Placed(SessionEvent recorded) => recorded with { Owner = "acme", RepositoryName = "xi" };

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The placed run", "acme/xi"),
            Placed(SessionEvent.ToolRan(Morning, "2026-09-14T09:01:00.000Z")),
            Placed(SessionEvent.ToolFailed(Morning, "2026-09-14T09:02:00.000Z")));

        var session = Assert.Single(await studio.SessionsIn("?repository=acme/xi"));

        // Every read is narrowed in the store, so a run whose events all name the Repository is counted in full.
        Assert.Equal(2, session.ToolCalls);
        Assert.Equal(1, session.Faults);
    }

    [Fact]
    public async Task Narrows_the_table_to_the_sessions_in_which_a_skill_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run that swept"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The run that did not"));
        await studio.Push(
            new SkillActivated("comment-sweep", "2026-09-14T09:05:00.000Z") { Session = Morning },
            new SkillActivated("tdd", "2026-09-14T14:05:00.000Z") { Session = Afternoon });

        Assert.Equal(
            ["The run that swept"],
            (await studio.SessionsIn("?skill=comment-sweep")).Select(session => session.Name));
    }

    [Fact]
    public async Task Leaves_a_session_the_skill_never_fired_in_out_even_when_it_ran_the_same_day()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The quiet run"));

        Assert.Empty(await studio.SessionsIn("?skill=comment-sweep"));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_skill_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run that swept"),
            SessionEvent.ToolRan(Morning, "2026-09-14T09:01:00.000Z"),
            SessionEvent.ToolFailed(Morning, "2026-09-14T09:02:00.000Z"));
        await studio.Push(new SkillActivated("comment-sweep", "2026-09-14T09:05:00.000Z") { Session = Morning });

        var session = Assert.Single(await studio.SessionsIn("?skill=comment-sweep"));

        Assert.Equal(2, session.ToolCalls);
        Assert.Equal(1, session.Faults);
    }

    [Fact]
    public async Task Narrows_the_table_by_the_span_the_repository_and_the_skill_together()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The run that matches", "acme/xi"),
            Ran(Afternoon, "2026-09-12T09:00:00.000Z", "The run outside the span", "acme/xi"),
            Ran(Evening, "2026-09-14T14:00:00.000Z", "The run in another repository", "acme/nu"));
        await studio.Push(
            new SkillActivated("tdd", "2026-09-14T09:05:00.000Z") { Session = Morning },
            new SkillActivated("tdd", "2026-09-12T09:05:00.000Z") { Session = Afternoon },
            new SkillActivated("tdd", "2026-09-14T14:05:00.000Z") { Session = Evening });

        var names = (await studio.SessionsIn("?from=2026-09-14&to=2026-09-14&repository=acme/xi&skill=tdd"))
            .Select(session => session.Name);

        Assert.Equal(["The run that matches"], names);
    }

    [Fact]
    public async Task Answers_with_an_empty_table_when_a_combination_matches_nothing()
    {
        using var studio = new StudioHost();

        await studio.Push(Ran(Morning, "2026-09-14T09:00:00.000Z", "The only run", "acme/xi"));
        await studio.Push(new SkillActivated("tdd", "2026-09-14T09:05:00.000Z") { Session = Morning });

        var answer = await studio.SessionAnswer("?repository=acme/nu&skill=tdd");

        // A combination that matches nothing must not read as a store that fell short.
        Assert.Empty(answer.Sessions);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Hides_neither_depth_from_a_table_nobody_narrowed_by_depth()
    {
        using var studio = new StudioHost();

        await BothDepthsRan(studio);

        Assert.Equal(["The thin run", "The full run"], (await studio.SessionsIn()).Select(session => session.Name));
    }

    [Fact]
    public async Task Narrows_the_table_to_the_runs_that_can_be_read_in_full()
    {
        using var studio = new StudioHost();

        await BothDepthsRan(studio);

        Assert.Equal(["The full run"], (await studio.SessionsIn("?depth=full")).Select(session => session.Name));
    }

    [Fact]
    public async Task Narrows_the_table_to_the_runs_that_were_never_traced()
    {
        using var studio = new StudioHost();

        await BothDepthsRan(studio);

        Assert.Equal(["The thin run"], (await studio.SessionsIn("?depth=thin")).Select(session => session.Name));
    }

    [Fact]
    public async Task Opens_a_whole_table_for_a_depth_nobody_has()
    {
        using var studio = new StudioHost();

        await BothDepthsRan(studio);

        // A hand-typed address that misspells a Depth must hide no run, as nobody asked for one to go.
        Assert.Equal(
            ["The thin run", "The full run"],
            (await studio.SessionsIn("?depth=deep")).Select(session => session.Name));
    }

    [Fact]
    public async Task Narrows_the_table_by_the_span_the_repository_the_skill_and_the_depth_together()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, "2026-09-14T09:00:00.000Z", "The run that matches", "acme/xi"),
            Ran(Afternoon, "2026-09-14T10:00:00.000Z", "The run that was never traced", "acme/xi"),
            Ran(Evening, "2026-09-12T09:00:00.000Z", "The run outside the span", "acme/xi"));
        await studio.Push(
            new SkillActivated("tdd", "2026-09-14T09:05:00.000Z") { Session = Morning },
            new SkillActivated("tdd", "2026-09-14T10:05:00.000Z") { Session = Afternoon },
            new SkillActivated("tdd", "2026-09-12T09:05:00.000Z") { Session = Evening });
        await studio.PushSpans(Morning, MorningTrace, Traced(MorningSpan));
        await studio.PushSpans(Evening, EveningTrace, Traced(EveningSpan));

        var names = (await studio.SessionsIn("?from=2026-09-14&to=2026-09-14&repository=acme/xi&skill=tdd&depth=full"))
            .Select(session => session.Name);

        Assert.Equal(["The run that matches"], names);
    }

    [Fact]
    public async Task Draws_a_table_nobody_narrowed_by_depth_even_when_the_trace_store_is_down()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await studio.Push(SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run"));

        var answer = await studio.SessionAnswer();

        // The list is the events store's answer, so a slow or broken trace store leaves no reader waiting.
        Assert.Equal(["The run"], answer.Sessions.Select(session => session.Name));
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Names_the_trace_store_rather_than_narrowing_by_a_depth_it_could_not_read()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await studio.Push(SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run"));

        var answer = await studio.SessionAnswer("?depth=full");

        // A guessed Depth would hide runs nobody asked to hide, so the table says what it cannot know instead.
        Assert.Empty(answer.Sessions);
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Names_the_trace_store_for_a_depth_it_could_not_read_even_with_the_telemetry_switch_off()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces, emitting: false);

        await studio.Push(SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The run"));

        var answer = await studio.SessionAnswer("?depth=full");

        // The store that emptied the table is the one to name, and a switch nobody flipped did not empty it.
        Assert.Empty(answer.Sessions);
        Assert.Contains("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    private static async Task BothDepthsRan(StudioHost studio)
    {
        await studio.Push(
            SessionEvent.Titled(Morning, "2026-09-14T09:00:00.000Z", "The full run"),
            SessionEvent.Titled(Afternoon, "2026-09-14T14:00:00.000Z", "The thin run"));

        await studio.PushSpans(Morning, MorningTrace, Traced(MorningSpan));
    }

    // Nothing but a span of the run: a Depth asks whether the trace store holds one, never what it says.
    private static RecordedSpan Traced(string id) =>
        new("claude_code.interaction", "2026-09-14T09:00:00Z", "2026-09-14T09:00:30Z", id);

    private static SessionEvent Ran(string session, string at, string title, string repository)
    {
        var placed = repository.Split('/');

        return SessionEvent.Titled(session, at, title) with { Owner = placed[0], RepositoryName = placed[1] };
    }
}
