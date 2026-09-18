using Skillworks.Core.Tests.TraceStore;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // A trace of its own for each run, as Claude Code never writes two runs into one.
    private const string MorningTrace = "7a1c0a9e0000400080000000000000b1";

    private const string AfternoonTrace = "7a1c0a9e0000400080000000000000b2";

    private const string EveningTrace = "7a1c0a9e0000400080000000000000b3";

    private const string MorningSpan = "c11c0a9e00000001";

    private const string AfternoonSpan = "c11c0a9e00000002";

    private const string EveningSpan = "c11c0a9e00000003";

    [Fact]
    public async Task Narrows_the_table_to_a_span_of_days_and_takes_both_ends_in()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(3), "09:00:00.000"), "The run before"),
            SessionEvent.Titled(Afternoon, At(DaysBack(2), "09:00:00.000"), "The first day"),
            SessionEvent.Titled(Evening, At(Yesterday, "09:00:00.000"), "The last day"));

        var names = (await studio.SessionsIn($"?from={Written(DaysBack(2))}&to={Written(Yesterday)}")).Select(session => session.Name);

        Assert.Equal(["The last day", "The first day"], names);
    }

    [Fact]
    public async Task Counts_a_span_of_days_in_whole_utc_days()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(DaysBack(2), "00:00:00.000"), "The first instant"),
            SessionEvent.Titled(Afternoon, At(DaysBack(2), "23:59:59.000"), "The last instant"));

        // A local day would put a late run on another day and drop it from the answer.
        Assert.Equal(2, (await studio.SessionsIn($"?from={Written(DaysBack(2))}&to={Written(DaysBack(2))}")).Count);
    }

    [Fact]
    public async Task Says_which_days_a_narrowed_table_covers_and_that_they_are_not_the_lookback()
    {
        using var studio = new StudioHost();

        var span = (await studio.SessionAnswer($"?from={Written(DaysBack(2))}&to={Written(Yesterday)}")).Head.Span;

        Assert.False(span.Lookback);
        Assert.Equal(DaysBack(2), span.From);
        Assert.Equal(Yesterday, span.To);
    }

    [Fact]
    public async Task Narrows_the_table_to_one_repository()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The chosen run", "acme/xi"),
            Ran(Afternoon, At(Yesterday, "14:00:00.000"), "The other run", "acme/nu"));

        Assert.Equal(["The chosen run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Answers_with_no_runs_for_a_repository_that_is_a_near_miss()
    {
        using var studio = new StudioHost();

        await studio.Push(Ran(Morning, At(Yesterday, "09:00:00.000"), "The chosen run", "acme/xi"));

        Assert.Empty(await studio.SessionsIn("?repository=acme/x"));
    }

    [Fact]
    public async Task Leaves_a_run_that_names_no_repository_out_when_one_is_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The placed run", "acme/xi"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The run from nowhere"));

        Assert.Equal(["The placed run"], (await studio.SessionsIn("?repository=acme/xi")).Select(session => session.Name));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_repository_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        SessionEvent Placed(SessionEvent recorded) => recorded with { Owner = "acme", RepositoryName = "xi" };

        await studio.Push(
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The placed run", "acme/xi"),
            Placed(SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000"))),
            Placed(SessionEvent.ToolFailed(Morning, At(Yesterday, "09:02:00.000"))));

        var answer = await studio.SessionAnswer("?repository=acme/xi");

        // Every read is narrowed in the store, so a run whose events all name the Repository is counted in full.
        Assert.Equal(Morning, Assert.Single(answer.Sessions).Id);
        Assert.Equal(2m, answer.Measured("toolCalls", Morning));
        Assert.Equal(1m, answer.Measured("faults", Morning));
    }

    [Fact]
    public async Task Narrows_the_table_to_the_sessions_in_which_a_skill_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run that swept"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The run that did not"));
        await studio.Push(
            new SkillActivated("comment-sweep", At(Yesterday, "09:05:00.000")) { Session = Morning },
            new SkillActivated("tdd", At(Yesterday, "14:05:00.000")) { Session = Afternoon });

        Assert.Equal(
            ["The run that swept"],
            (await studio.SessionsIn("?skill=comment-sweep")).Select(session => session.Name));
    }

    [Fact]
    public async Task Leaves_a_session_the_skill_never_fired_in_out_even_when_it_ran_the_same_day()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The quiet run"));

        Assert.Empty(await studio.SessionsIn("?skill=comment-sweep"));
    }

    [Fact]
    public async Task Keeps_a_session_whole_when_a_skill_narrows_the_table_to_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run that swept"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:00.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:02:00.000")));
        await studio.Push(new SkillActivated("comment-sweep", At(Yesterday, "09:05:00.000")) { Session = Morning });

        var answer = await studio.SessionAnswer("?skill=comment-sweep");

        Assert.Equal(Morning, Assert.Single(answer.Sessions).Id);
        Assert.Equal(2m, answer.Measured("toolCalls", Morning));
        Assert.Equal(1m, answer.Measured("faults", Morning));
    }

    [Fact]
    public async Task Narrows_the_table_by_the_span_the_repository_and_the_skill_together()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The run that matches", "acme/xi"),
            Ran(Afternoon, At(DaysBack(3), "09:00:00.000"), "The run outside the span", "acme/xi"),
            Ran(Evening, At(Yesterday, "14:00:00.000"), "The run in another repository", "acme/nu"));
        await studio.Push(
            new SkillActivated("tdd", At(Yesterday, "09:05:00.000")) { Session = Morning },
            new SkillActivated("tdd", At(DaysBack(3), "09:05:00.000")) { Session = Afternoon },
            new SkillActivated("tdd", At(Yesterday, "14:05:00.000")) { Session = Evening });

        var names = (await studio.SessionsIn($"?from={Written(Yesterday)}&to={Written(Yesterday)}&repository=acme/xi&skill=tdd"))
            .Select(session => session.Name);

        Assert.Equal(["The run that matches"], names);
    }

    [Fact]
    public async Task Answers_with_an_empty_table_when_a_combination_matches_nothing()
    {
        using var studio = new StudioHost();

        await studio.Push(Ran(Morning, At(Yesterday, "09:00:00.000"), "The only run", "acme/xi"));
        await studio.Push(new SkillActivated("tdd", At(Yesterday, "09:05:00.000")) { Session = Morning });

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
            Ran(Morning, At(Yesterday, "09:00:00.000"), "The run that matches", "acme/xi"),
            Ran(Afternoon, At(Yesterday, "10:00:00.000"), "The run that was never traced", "acme/xi"),
            Ran(Evening, At(DaysBack(3), "09:00:00.000"), "The run outside the span", "acme/xi"));
        await studio.Push(
            new SkillActivated("tdd", At(Yesterday, "09:05:00.000")) { Session = Morning },
            new SkillActivated("tdd", At(Yesterday, "10:05:00.000")) { Session = Afternoon },
            new SkillActivated("tdd", At(DaysBack(3), "09:05:00.000")) { Session = Evening });
        await studio.PushSpans(Morning, MorningTrace, Traced(MorningSpan));
        await studio.PushSpans(Evening, EveningTrace, Traced(EveningSpan));

        // The store reads the block a Span arrived in, and these arrived now, so the days asked for reach today.
        var span = $"?from={Written(Yesterday)}&to={Written(Today)}";

        var names = (await studio.SessionsIn($"{span}&repository=acme/xi&skill=tdd&depth=full"))
            .Select(session => session.Name);

        Assert.Equal(["The run that matches"], names);
    }

    [Fact]
    public async Task Draws_a_table_nobody_narrowed_by_depth_even_when_the_trace_store_is_down()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer();

        // The list is the events store's answer, so a slow or broken trace store leaves no reader waiting.
        Assert.Equal(["The run"], answer.Sessions.Select(session => session.Name));
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Leaves_the_table_standing_and_names_the_trace_store_for_a_depth_it_could_not_read()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer("?depth=full");

        // A guessed Depth would hide runs nobody asked to hide.
        Assert.Equal(["The run"], answer.Sessions.Select(session => session.Name));
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Names_the_trace_store_for_a_depth_it_could_not_read_even_with_the_telemetry_switch_off()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces, emitting: false);

        await studio.Push(SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer("?depth=full");

        // The store that could not answer is the one to name, and a switch nobody flipped is not it.
        Assert.Equal(["The run"], answer.Sessions.Select(session => session.Name));
        Assert.Contains("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Leaves_the_table_standing_and_names_the_trace_store_for_half_an_answer_of_depths()
    {
        // One of the two runs the store holds spans for, so its answer fills up and cuts the rest.
        using var studio = new StudioHost(mostSessions: 1);

        await EachHalfOfDepthRan(studio);

        var answer = await studio.SessionAnswer("?depth=full");

        // A run the store left out of half an answer would go missing from the table without a word.
        Assert.Equal(3, answer.Sessions.Count);
        Assert.Equal("shortened", answer.Gap.Kind);
        Assert.Contains("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Draws_a_table_nobody_narrowed_by_depth_even_when_the_trace_store_would_cut_its_answer_short()
    {
        using var studio = new StudioHost(mostSessions: 1);

        await EachHalfOfDepthRan(studio);

        var answer = await studio.SessionAnswer();

        // Nobody asked for a Depth, so the trace store was never read and could not fall short.
        Assert.Equal(3, answer.Sessions.Count);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Leaves_a_run_whose_words_were_withheld_out_of_a_table_narrowed_to_full()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        // The withheld run's Spans are whole, so the Spans half alone would have listed it.
        Assert.Equal(["The full run"], (await studio.SessionsIn("?depth=full")).Select(session => session.Name));
    }

    [Fact]
    public async Task Keeps_a_run_whose_words_were_withheld_in_a_table_narrowed_to_thin()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        Assert.Contains("The withheld run", (await studio.SessionsIn("?depth=thin")).Select(session => session.Name));
    }

    [Fact]
    public async Task Keeps_a_run_that_carries_its_words_and_no_spans_in_a_table_narrowed_to_thin()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        Assert.Contains("The untraced run", (await studio.SessionsIn("?depth=thin")).Select(session => session.Name));
    }

    [Fact]
    public async Task Opens_a_run_the_table_called_full_as_full()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        var listed = Assert.Single(await studio.SessionsIn("?depth=full"));

        Assert.Equal("full", (await studio.StepAnswer(listed.Id)).Depth);
    }

    [Fact]
    public async Task Opens_a_run_the_table_called_thin_as_thin()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        var listed = (await studio.SessionsIn("?depth=thin")).First(session => session.Name == "The withheld run");

        Assert.Equal("thin", (await studio.StepAnswer(listed.Id)).Depth);
    }

    [Fact]
    public async Task Asks_the_events_store_no_more_when_the_table_is_narrowed_by_depth()
    {
        // Down only before the two days the lookback covers, so nothing here breaks and every route is recorded.
        using var events = BrokenEventsStore.DownBefore(Yesterday);
        using var studio = new StudioHost(events: events, lookbackDays: 2);

        await EachHalfOfDepthRan(studio);

        Assert.NotEmpty(await studio.SessionsIn());
        var plain = events.Asked;

        Assert.NotEmpty(await studio.SessionsIn("?depth=full"));

        Assert.Equal(plain.Order(), events.Asked.Skip(plain.Count).Order());
    }

    private static async Task EachHalfOfDepthRan(StudioHost studio)
    {
        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The full run"),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:10.000"), "Fix the build"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The withheld run"),
            SessionEvent.PromptWithheld(Afternoon, At(Yesterday, "14:00:10.000"), 1_840),
            SessionEvent.Titled(Evening, At(Yesterday, "19:00:00.000"), "The untraced run"),
            SessionEvent.Prompted(Evening, At(Yesterday, "19:00:10.000"), "Push it"));

        await studio.PushSpans(Morning, MorningTrace, Traced(MorningSpan));
        await studio.PushSpans(Afternoon, AfternoonTrace, Traced(AfternoonSpan));
    }

    private static async Task BothDepthsRan(StudioHost studio)
    {
        await studio.Push(
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The full run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The thin run"));

        await studio.PushSpans(Morning, MorningTrace, Traced(MorningSpan));
    }

    // Nothing but a span of the run: a Depth asks whether the trace store holds one, never what it says.
    private static RecordedSpan Traced(string id) =>
        new("claude_code.interaction", At(Yesterday, "09:00:00"), At(Yesterday, "09:00:30"), id);

    private static SessionEvent Ran(string session, string at, string title, string repository)
    {
        var placed = repository.Split('/');

        return SessionEvent.Titled(session, at, title) with { Owner = placed[0], RepositoryName = placed[1] };
    }
}
