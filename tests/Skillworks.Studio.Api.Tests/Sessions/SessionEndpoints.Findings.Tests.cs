using System.Text.Json.Nodes;
using Skillworks.Core.Tests.TraceStore;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;
using Skillworks.Studio.Api.Tests.Sessions.Rows;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string FindingTrace = "7a1c0a9e0000400080000000000000e5";

    private const string SeenSpan = "f11c0a9e00000001";

    private const string PausedSpan = "f11c0a9e00000002";

    private const string GuardSpan = "f11c0a9e00000003";

    private static readonly string[] AgentSpans = ["f11c0a9e00000004", "f11c0a9e00000006", "f11c0a9e00000008"];

    private static readonly string[] ThoughtSpans = ["f11c0a9e00000005", "f11c0a9e00000007", "f11c0a9e00000009"];

    private static readonly string[] AgentNames = ["Find the leak", "Review the diff", "Read the tests"];

    [Fact]
    public async Task Answers_with_the_findings_the_events_alone_measure_and_again_once_the_spans_have_landed()
    {
        using var studio = new StudioHost();

        await Built(studio);

        var lines = await studio.StepLines(Morning);

        Assert.Equal(
            ["head", "exchanges", "activations", "context", "findings", "steps", "trace", "agents", "split", "findings", "end"],
            lines.Select(StudioHost.KindOf));
    }

    [Fact]
    public async Task Names_a_bar_the_events_alone_crossed_without_waiting_for_the_trace_store()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(traces: traces);

        await studio.Push(
            Failing(At(Yesterday, "09:00:05.000"), "npm test"),
            Failing(At(Yesterday, "09:00:10.000"), "npm test"),
            Failing(At(Yesterday, "09:00:15.000"), "npm test"));

        // The first findings line lands with the events, so a trace store that never answers leaves no empty list.
        var first = await studio.FirstStepLines(Morning, 5);
        var found = StudioHost.Read<FindingRow[]>(first[^1]["findings"]);

        Assert.Equal("findings", StudioHost.KindOf(first[^1]));
        Assert.Equal(3, Assert.Single(found, finding => finding.Kind == "failingAgain").Figure);
    }

    [Fact]
    public async Task Says_the_bars_only_a_span_can_measure_are_not_known_until_the_spans_have_landed()
    {
        using var studio = new StudioHost();

        await Built(studio);
        await studio.PushSpans(Morning, FindingTrace, Guarded(GuardSpan, At(Yesterday, "09:00:07"), At(Yesterday, "09:00:09")));

        var first = await studio.FirstStepLines(Morning, 5);
        var found = StudioHost.Read<FindingRow[]>(first[^1]["findings"]);

        // Nothing has been measured against yet, so the three read Not known and later fill in.
        Assert.All(found, finding => Assert.Null(finding.Figure));
        Assert.Equal(0.2m, Crossed(await studio.FindingsIn(Morning), "hooks")?.Figure);
    }

    [Fact]
    public async Task Sends_a_finding_with_the_figure_it_crossed_on_and_the_moment_it_happened()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:05.000")));

        var line = await studio.StepLine("findings", Morning);

        Assert.Equal(["findings", "kind"], StudioHost.Fields(line));
        Assert.Equal(
            ["atUtc", "bar", "figure", "kind", "lengthMs", "step", "subject"],
            StudioHost.Fields(line["findings"]?[0]));
    }

    [Fact]
    public async Task Names_nothing_in_a_run_that_crossed_no_bar()
    {
        using var studio = new StudioHost();

        await Built(studio);
        await studio.PushSpans(Morning, FindingTrace, Watched(SeenSpan, "toolu_01"));

        // Every bar was measured and none was crossed, so a clean run is named as clean by saying nothing.
        Assert.Equal("full", (await studio.StepAnswer(Morning)).Depth);
        Assert.Empty(await studio.FindingsIn(Morning));
    }

    [Fact]
    public async Task Names_the_same_call_failing_over_and_over()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Failing(At(Yesterday, "09:00:05.000"), "npm test"),
            Failing(At(Yesterday, "09:00:10.000"), "npm test"),
            Failing(At(Yesterday, "09:00:15.000"), "npm test"));

        var finding = Crossed(await studio.FindingsIn(Morning), "failingAgain");

        Assert.Equal(3, finding?.Figure);
        Assert.Equal("npm test", finding?.Subject);
    }

    [Fact]
    public async Task Says_nothing_of_a_call_that_failed_fewer_times_than_the_bar()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Failing(At(Yesterday, "09:00:05.000"), "npm test"),
            Failing(At(Yesterday, "09:00:10.000"), "npm test"));

        Assert.Null(Crossed(await studio.FindingsIn(Morning), "failingAgain"));
    }

    [Fact]
    public async Task Keeps_three_different_calls_that_failed_once_each_apart()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Failing(At(Yesterday, "09:00:05.000"), "npm test"),
            Failing(At(Yesterday, "09:00:10.000"), "npm run build"),
            Failing(At(Yesterday, "09:00:15.000"), "npm run lint"));

        // Three things going wrong once each is a hard afternoon, not an agent stuck on one of them.
        Assert.Null(Crossed(await studio.FindingsIn(Morning), "failingAgain"));
    }

    [Fact]
    public async Task Names_one_file_edited_over_and_over()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Editing(At(Yesterday, "09:00:05.000"), "src/App.tsx"),
            Editing(At(Yesterday, "09:00:10.000"), "src/App.tsx"),
            Editing(At(Yesterday, "09:00:15.000"), "src/App.tsx"),
            Editing(At(Yesterday, "09:00:20.000"), "src/App.tsx"),
            Editing(At(Yesterday, "09:00:25.000"), "src/App.tsx"));

        var finding = Crossed(await studio.FindingsIn(Morning), "editedAgain");

        Assert.Equal(5, finding?.Figure);
        Assert.Equal("src/App.tsx", finding?.Subject);
    }

    [Fact]
    public async Task Counts_a_notebook_edited_over_and_over_as_the_same_file()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Noting(At(Yesterday, "09:00:05.000"), "src/Report.ipynb"),
            Noting(At(Yesterday, "09:00:10.000"), "src/Report.ipynb"),
            Noting(At(Yesterday, "09:00:15.000"), "src/Report.ipynb"),
            Noting(At(Yesterday, "09:00:20.000"), "src/Report.ipynb"),
            Noting(At(Yesterday, "09:00:25.000"), "src/Report.ipynb"));

        // NotebookEdit names its file under a key of its own, and a notebook is a file a reader went back to.
        Assert.Equal("src/Report.ipynb", Crossed(await studio.FindingsIn(Morning), "editedAgain")?.Subject);
    }

    [Fact]
    public async Task Says_nothing_of_a_file_edited_fewer_times_than_the_bar()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Editing(At(Yesterday, "09:00:05.000"), "src/App.tsx"),
            Editing(At(Yesterday, "09:00:10.000"), "src/App.tsx"),
            Editing(At(Yesterday, "09:00:15.000"), "src/App.tsx"),
            Editing(At(Yesterday, "09:00:20.000"), "src/App.tsx"));

        Assert.Null(Crossed(await studio.FindingsIn(Morning), "editedAgain"));
    }

    [Fact]
    public async Task Names_a_run_that_hit_a_rate_limit()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:05.000")),
            SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:25.000")));

        Assert.Equal(2, Crossed(await studio.FindingsIn(Morning), "rateLimited")?.Figure);
    }

    [Fact]
    public async Task Says_nothing_of_a_model_error_that_was_not_a_rate_limit()
    {
        using var studio = new StudioHost();

        await studio.Push(new SessionEvent(Morning, "api_error", At(Yesterday, "09:00:05.000")) { ErrorType = "Overloaded" });

        // A busy model is nothing a person can act on, and naming it would name every run on a busy day.
        Assert.Null(Crossed(await studio.FindingsIn(Morning), "rateLimited"));
    }

    [Fact]
    public async Task Names_a_run_whose_prompt_cache_was_rebuilt()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { CacheReadTokens = 60_000 },
            Turn(At(Yesterday, "09:05:00.000")) with { CacheReadTokens = 1_000, CacheCreationTokens = 61_000 });

        Assert.Equal(1, Crossed(await studio.FindingsIn(Morning), "cacheRebuilt")?.Figure);
    }

    [Fact]
    public async Task Says_nothing_of_a_run_that_only_wrote_its_cache_once_at_the_start()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { CacheCreationTokens = 60_000 },
            Turn(At(Yesterday, "09:05:00.000")) with { CacheReadTokens = 60_000 });

        Assert.Null(Crossed(await studio.FindingsIn(Morning), "cacheRebuilt"));
    }

    [Fact]
    public async Task Names_a_run_whose_context_came_near_its_limit()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Turn(At(Yesterday, "09:00:00.000")) with { InputTokens = 100_000 },
            Turn(At(Yesterday, "09:05:00.000")) with { InputTokens = 850_000 });

        Assert.Equal(0.85m, Crossed(await studio.FindingsIn(Morning), "nearTheLimit")?.Figure);
    }

    [Fact]
    public async Task Says_nothing_of_a_run_whose_context_stayed_well_inside_its_limit()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with { InputTokens = 100_000 });

        Assert.Null(Crossed(await studio.FindingsIn(Morning), "nearTheLimit"));
    }

    [Fact]
    public async Task Says_nothing_of_a_full_context_where_no_model_named_a_limit()
    {
        using var studio = new StudioHost();

        await studio.Push(Turn(At(Yesterday, "09:00:00.000")) with { Model = ModelWithNoMarker, InputTokens = 900_000 });

        // A window nobody stated cannot be neared, and inventing one would make some run look doomed.
        Assert.Null(Crossed(await studio.FindingsIn(Morning), "nearTheLimit"));
    }

    [Fact]
    public async Task Names_a_run_that_gave_a_large_share_of_its_working_time_to_hooks()
    {
        using var studio = new StudioHost();

        await Built(studio);
        await studio.PushSpans(Morning, FindingTrace, Guarded(GuardSpan, At(Yesterday, "09:00:07"), At(Yesterday, "09:00:09")));

        // Two seconds of hooks in ten seconds of work, where the five quiet seconds count for neither.
        Assert.Equal(0.2m, Crossed(await studio.FindingsIn(Morning), "hooks")?.Figure);
    }

    [Fact]
    public async Task Says_nothing_of_a_run_whose_hooks_took_a_small_share_of_its_working_time()
    {
        using var studio = new StudioHost();

        await Built(studio);
        await studio.PushSpans(Morning, FindingTrace, Guarded(GuardSpan, At(Yesterday, "09:00:07"), At(Yesterday, "09:00:08")));

        Assert.Null(Crossed(await studio.FindingsIn(Morning), "hooks"));
    }

    [Fact]
    public async Task Names_a_run_that_spent_a_long_time_waiting_for_permission()
    {
        using var studio = new StudioHost();

        await Asking(studio);
        await studio.PushSpans(
            Morning,
            FindingTrace,
            Paused(PausedSpan, "toolu_01", At(Yesterday, "09:00:00"), At(Yesterday, "09:03:00")));

        var finding = Crossed(await studio.FindingsIn(Morning), "waiting");

        Assert.Equal(180_000, finding?.Figure);
        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), finding?.AtUtc);
    }

    [Fact]
    public async Task Says_nothing_of_a_run_whose_wait_for_permission_was_short()
    {
        using var studio = new StudioHost();

        await Asking(studio);
        await studio.PushSpans(
            Morning,
            FindingTrace,
            Paused(PausedSpan, "toolu_01", At(Yesterday, "09:00:00"), At(Yesterday, "09:01:00")));

        Assert.Null(Crossed(await studio.FindingsIn(Morning), "waiting"));
    }

    [Fact]
    public async Task Names_a_subagent_that_cost_far_more_than_its_siblings()
    {
        using var studio = new StudioHost();

        await TwoAgentsRan(studio, 0.40m, 0.10m);

        var finding = Crossed(await studio.FindingsIn(Morning), "costlySubagent");

        Assert.Equal(4m, finding?.Figure);
        Assert.Equal("Find the leak", finding?.Subject);
    }

    [Fact]
    public async Task Says_nothing_of_subagents_that_cost_much_the_same_as_each_other()
    {
        using var studio = new StudioHost();

        await TwoAgentsRan(studio, 0.40m, 0.20m);

        Assert.Null(Crossed(await studio.FindingsIn(Morning), "costlySubagent"));
    }

    [Fact]
    public async Task Weighs_a_costly_subagent_against_the_middle_of_its_siblings_and_not_their_sum()
    {
        using var studio = new StudioHost();

        await ThreeAgentsRan(studio, 0.60m, 0.20m, 0.20m);

        // Two siblings at twenty pence put the middle at twenty, which three times over is where sixty crosses.
        Assert.Equal(3m, Crossed(await studio.FindingsIn(Morning), "costlySubagent")?.Figure);
    }

    [Fact]
    public async Task Says_the_three_bars_only_a_span_can_measure_are_not_known_in_a_thin_run()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Find the leak"),
            SessionEvent.AgentRan(Morning, At(Yesterday, "09:00:40.000"), "toolu_a", "Find the leak", lengthMs: 30_000),
            SessionEvent.AgentRan(Morning, At(Yesterday, "09:01:40.000"), "toolu_b", "Review the diff", lengthMs: 30_000));

        var answer = await studio.StepAnswer(Morning);

        // Left out, a bar nobody could measure would read as a bar that was measured and found clean.
        Assert.Equal("thin", answer.Depth);
        Assert.Equal(["hooks", "waiting", "costlySubagent"], answer.Findings.Select(finding => finding.Kind));
        Assert.All(answer.Findings, finding => Assert.Null(finding.Figure));
    }

    [Fact]
    public async Task Says_nothing_of_a_costly_subagent_in_a_thin_run_that_started_no_two_subagents()
    {
        using var studio = new StudioHost();

        await Built(studio);

        var answer = await studio.StepAnswer(Morning);

        // The events name no two Agent calls, so there were never siblings to compare and no Span could add any.
        Assert.Equal("thin", answer.Depth);
        Assert.Equal(["hooks", "waiting"], answer.Findings.Select(finding => finding.Kind));
    }

    [Fact]
    public async Task Points_a_finding_at_the_step_it_happened_on()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Failing(At(Yesterday, "09:00:05.000"), "npm test"),
            Failing(At(Yesterday, "09:00:10.000"), "npm test"),
            Failing(At(Yesterday, "09:00:15.000"), "npm test"));

        var answer = await studio.StepAnswer(Morning);
        var finding = Crossed(answer.Findings, "failingAgain");

        // The last go at it, which is where a reader picking the Finding up wants to start reading.
        Assert.Equal(answer.Steps[^1].Id, finding?.Step);
        Assert.Equal(Moment(At(Yesterday, "09:00:15.000")), finding?.AtUtc);
    }

    [Fact]
    public async Task Names_no_finding_in_a_run_no_store_holds()
    {
        using var studio = new StudioHost();

        Assert.Empty(await studio.FindingsIn(Morning));
    }

    private static FindingRow? Crossed(IReadOnlyList<FindingRow> found, string kind) =>
        found.SingleOrDefault(finding => finding.Kind == kind);

    // Five seconds of model, five of tool and five of quiet between them, which no bar of its own crosses.
    private static Task Built(StudioHost studio) =>
        studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:05.000"), 5_000, source: "main"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:12.000"), "Bash", 5_000, "toolu_01"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:15.000"), "Built."));

    // A five-minute Tool call, so the wait a Span puts inside it has room to cross a bar counted in minutes.
    private static Task Asking(StudioHost studio) =>
        studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Drop the table"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:05:00.000"), "Bash", 300_000, "toolu_01"),
            SessionEvent.Answered(Morning, At(Yesterday, "09:05:01.000"), "Dropped."));

    private static Task TwoAgentsRan(StudioHost studio, decimal first, decimal second) =>
        AgentsRan(studio, [first, second]);

    private static Task ThreeAgentsRan(StudioHost studio, decimal first, decimal second, decimal third) =>
        AgentsRan(studio, [first, second, third]);

    // One Agent Tool call and one Turn each, a minute apart, with the Spans that put the Turn on the Subagent.
    private static async Task AgentsRan(StudioHost studio, IReadOnlyList<decimal> costs)
    {
        var events = new List<SessionEvent> { SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Find the leak") };
        var spans = new List<RecordedSpan>();

        for (var agent = 0; agent < costs.Count; agent++)
        {
            var minute = $"09:0{agent}";

            events.Add(SessionEvent.Turned(Morning, At(Yesterday, $"{minute}:25.000"), 3_000, costs[agent], $"req_{agent}"));
            events.Add(SessionEvent.AgentRan(
                Morning,
                At(Yesterday, $"{minute}:40.000"),
                $"toolu_{agent}",
                AgentNames[agent],
                "Explore",
                "Read",
                30_000));

            spans.Add(Around(AgentSpans[agent], $"toolu_{agent}", $"agent-{agent}", At(Yesterday, $"{minute}:11"), At(Yesterday, $"{minute}:39")));
            spans.Add(Thinking(ThoughtSpans[agent], $"req_{agent}", $"agent-{agent}", At(Yesterday, $"{minute}:22")));
        }

        await studio.Push([.. events]);
        await studio.PushSpans(Morning, FindingTrace, [.. spans]);
    }

    // Any Span at all lifts a run to Full, and this one says nothing beyond that.
    private static RecordedSpan Watched(string id, string toolUse) =>
        new("claude_code.tool", At(Yesterday, "09:00:07"), At(Yesterday, "09:00:12"), id, ToolUse: toolUse);

    private static RecordedSpan Paused(string id, string toolUse, string at, string until) =>
        new("claude_code.tool.blocked_on_user", at, until, id, ToolUse: toolUse);

    private static RecordedSpan Guarded(string id, string at, string until) =>
        new("claude_code.hook", at, until, id);

    private static RecordedSpan Around(string id, string toolUse, string agent, string at, string until) =>
        new("claude_code.tool.execution", at, until, id, Agent: agent, ToolUse: toolUse);

    private static RecordedSpan Thinking(string id, string request, string agent, string at) =>
        new("claude_code.llm_request", at, at, id, Agent: agent, Request: request);

    private static SessionEvent Failing(string at, string command) =>
        SessionEvent.ToolFailed(Morning, at) with { ToolInput = new JsonObject { ["command"] = command }.ToJsonString() };

    private static SessionEvent Editing(string at, string file) =>
        SessionEvent.ToolRan(Morning, at, "Edit") with { ToolInput = new JsonObject { ["file_path"] = file }.ToJsonString() };

    private static SessionEvent Noting(string at, string notebook) =>
        SessionEvent.ToolRan(Morning, at, "NotebookEdit") with
        {
            ToolInput = new JsonObject { ["notebook_path"] = notebook }.ToJsonString(),
        };
}
