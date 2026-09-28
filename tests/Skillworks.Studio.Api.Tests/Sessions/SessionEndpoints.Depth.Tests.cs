using Skillworks.Core.Tests.Shared.Stores.TraceStore;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;
using Skillworks.Studio.Api.Tests.Sessions.Answers;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // A trace of its own for each run, as Claude Code never writes two runs into one.
    private const string MorningTrace = "7a1c0a9e0000400080000000000000b1";

    private const string AfternoonTrace = "7a1c0a9e0000400080000000000000b2";

    private const string MorningSpan = "c11c0a9e00000001";

    private const string AfternoonSpan = "c11c0a9e00000002";

    [Fact]
    public async Task Gives_each_row_its_depth_full_where_traced_and_thin_where_not()
    {
        using var studio = new StudioHost();

        await BothDepthsRan(studio);

        var answer = await studio.SessionAnswer();

        Assert.Equal(["The thin run", "The full run"], answer.Sessions.Select(session => session.Name));
        Assert.Equal("full", answer.Depths[Morning]);
        Assert.Equal("thin", answer.Depths[Afternoon]);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Reads_a_run_whose_words_were_withheld_as_thin_however_whole_its_spans()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        var answer = await studio.SessionAnswer();

        // The withheld run still has its row, as withheld words hide what was said and not that it ran.
        Assert.Contains("The withheld run", answer.Sessions.Select(session => session.Name));
        Assert.Equal("thin", answer.Depths[Afternoon]);
        Assert.Equal("full", answer.Depths[Morning]);
    }

    [Fact]
    public async Task Reads_a_run_that_carries_its_words_and_no_spans_as_thin()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        Assert.Equal("thin", (await studio.SessionAnswer()).Depths[Evening]);
    }

    [Fact]
    public async Task Leaves_the_depth_a_dash_and_names_the_trace_store_when_it_is_down()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer();

        // A Depth nobody could read is never Thin, as Thin would tell a reader the run has nothing more to show.
        Assert.Equal(["The run"], answer.Sessions.Select(session => session.Name));
        Assert.False(answer.Depths.ContainsKey(Morning));
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Names_the_trace_store_for_a_depth_it_could_not_read_even_with_the_telemetry_switch_off()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces, emitting: false);

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var answer = await studio.SessionAnswer();

        // The store that could not answer is the one to name, and a switch nobody flipped is not it.
        Assert.Equal(["The run"], answer.Sessions.Select(session => session.Name));
        Assert.Contains("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Still_reads_a_run_whose_words_were_withheld_as_thin_when_the_trace_store_is_down()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The withheld run"),
            SessionEvent.PromptWithheld(Morning, At(Yesterday, "09:00:10.000"), 1_840));

        // Withheld words are enough on their own to make a run Thin, so no Span could change it.
        Assert.Equal("thin", (await studio.SessionAnswer()).Depths[Morning]);
    }

    [Fact]
    public async Task Reads_every_depth_in_days_that_hold_more_traced_runs_than_one_read_names()
    {
        using var studio = new StudioHost(mostSessions: 1);

        await EachHalfOfDepthRan(studio);

        // Traced runs with no row, so a read of every run the days hold would fill up and cut the rows' own.
        foreach (var unlisted in Enumerable.Range(1, 3))
        {
            await studio.PushSpans(
                Numbered(700 + unlisted),
                $"7a1c0a9e0000400080000000000007{unlisted:D2}",
                Traced($"c11c0a9e000007{unlisted:D2}"));
        }

        var answer = await studio.SessionAnswer();

        Assert.Equal(3, answer.Sessions.Count);
        Assert.Equal("full", answer.Depths[Morning]);
        Assert.Equal("thin", answer.Depths[Afternoon]);
        Assert.Equal("thin", answer.Depths[Evening]);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Reads_the_depth_of_the_rows_a_later_read_loaded()
    {
        using var studio = new StudioHost(mostSessions: 1);

        var traced = Numbered(RowsPerRead);
        var untraced = Numbered(RowsPerRead + 1);

        await studio.Push(Asked(RowsPerRead + 2));
        await studio.PushSpans(traced, MorningTrace, Traced(MorningSpan));

        var second = await studio.LaterSessionAnswer(await studio.SessionAnswer());

        Assert.Equal([traced, untraced], second.Sessions.Select(session => session.Id));
        Assert.Equal("full", second.Depths[traced]);
        Assert.Equal("thin", second.Depths[untraced]);
        Assert.DoesNotContain("trace store", second.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Draws_the_rows_while_the_trace_store_is_still_out()
    {
        using var traces = BrokenTraceStore.Stalling();
        using var studio = new StudioHost(traces: traces);

        await PushWithPrompts(studio, SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The run"));

        var lines = await studio.SessionLines(count: 2, closeAfter: traces.FirstAsked);

        Assert.Equal(["head", "sessions"], lines.Select(StudioHost.KindOf));
        Assert.Equal(["The run"], SessionsAnswer.RowsIn(lines).Select(row => row.Name));

        // The close waited for the store to be asked anything, and only this says it was asked for the rows' Depths.
        Assert.Contains("span.session.id", await traces.FirstAsked, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Asks_the_trace_store_nothing_when_no_row_stands()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        var answer = await studio.SessionAnswer();

        // No row, no Depth, so a store with nothing to answer for costs an empty list no sentence.
        Assert.Empty(traces.Asked);
        Assert.DoesNotContain("trace store", answer.Gap.Missing ?? "", StringComparison.Ordinal);
    }

    [Fact]
    public async Task Opens_a_run_the_list_called_full_as_full()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        Assert.Equal("full", (await studio.SessionAnswer()).Depths[Morning]);
        Assert.Equal("full", (await studio.StepAnswer(Morning)).Depth);
    }

    [Fact]
    public async Task Opens_a_run_the_list_called_thin_as_thin()
    {
        using var studio = new StudioHost();

        await EachHalfOfDepthRan(studio);

        Assert.Equal("thin", (await studio.SessionAnswer()).Depths[Afternoon]);
        Assert.Equal("thin", (await studio.StepAnswer(Afternoon)).Depth);
    }

    private static async Task EachHalfOfDepthRan(StudioHost studio)
    {
        await PushWithPrompts(
            studio,
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
        await PushWithPrompts(
            studio,
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:00.000"), "The full run"),
            SessionEvent.Titled(Afternoon, At(Yesterday, "14:00:00.000"), "The thin run"));

        await studio.PushSpans(Morning, MorningTrace, Traced(MorningSpan));
    }

    // Nothing but a span of the run: a Depth asks whether the trace store holds one, never what it says.
    private static RecordedSpan Traced(string id) =>
        new("claude_code.interaction", At(Yesterday, "09:00:00"), At(Yesterday, "09:00:30"), id);
}
