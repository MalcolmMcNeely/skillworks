using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    // Over the page one read of the store holds, so a long run's later steps prove the reader asks again.
    private const int MoreEventsThanOnePageHolds = 1_100;

    [Fact]
    public async Task Answers_one_run_with_a_head_then_the_panels_then_its_steps_then_an_end()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var lines = await studio.StepLines(Morning);

        // A screen draws once the steps land, so everything it draws beside them has to be there already.
        Assert.Equal(
            ["head", "exchanges", "activations", "context", "findings", "steps", "trace", "agents", "split", "findings", "end"],
            lines.Select(StudioHost.KindOf));
    }

    [Fact]
    public async Task Answers_one_run_with_lines_that_hold_only_what_a_screen_reads()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var head = await studio.StepLine("head", Morning);
        var page = await studio.StepLine("steps", Morning);

        Assert.Equal(["kind", "session"], StudioHost.Fields(head));
        Assert.Equal(
            ["cost", "faults", "friction", "id", "lengthMs", "name", "person", "repository", "running", "startedUtc", "toolCalls"],
            StudioHost.Fields(head["session"]));

        Assert.Equal(["kind", "steps"], StudioHost.Fields(page));
        Assert.Equal(["atUtc", "fault", "id", "kind", "lengthMs", "tool", "words"], StudioHost.Fields(page["steps"]?[0]));
    }

    [Fact]
    public async Task Opens_the_run_the_table_named_with_the_same_figures_the_row_carried()
    {
        using var studio = new StudioHost();

        SessionEvent[] recorded =
        [
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:05.000"), "The build fix"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:20.000"), 2_000, 0.42m),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:30.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:00:40.000")),
            SessionEvent.Refused(Morning, At(Yesterday, "09:00:50.000")),
            SessionEvent.Answered(Morning, At(Yesterday, "09:01:00.000"), "Done"),
        ];

        // Claude Code names the person and the repository on every event of a run.
        await studio.Push(
            [.. recorded.Select(each => each with { Person = "grace@acme.test", Owner = "malcolmania", RepositoryName = "skillworks" })]);

        var run = (await studio.StepAnswer(Morning)).Run;

        Assert.NotNull(run);
        Assert.Equal(Morning, run.Id);
        Assert.Equal("The build fix", run.Name);
        Assert.Equal("malcolmania/skillworks", run.Repository);
        Assert.Equal("grace@acme.test", run.Person);
        Assert.Equal(Moment(At(Yesterday, "09:00:00.000")), run.StartedUtc);
        Assert.Equal((long)TimeSpan.FromMinutes(1).TotalMilliseconds, run.LengthMs);
        Assert.Equal(2, run.ToolCalls);
        Assert.Equal(0.42m, run.Cost);
        Assert.Equal(1, run.Faults);
        Assert.Equal(1, run.Friction);
    }

    [Fact]
    public async Task Draws_a_step_for_the_prompt_the_turn_the_tool_call_and_the_answer()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:10.000"), 2_000),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:20.000"), "Bash", 4_000),
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:30.000"), "Built."));

        var steps = await studio.StepsIn(Morning);

        Assert.Equal(["prompt", "turn", "tool", "answer"], steps.Select(step => step.Kind));
        Assert.Equal(["Fix the build", "claude-opus-5", null, "Built."], steps.Select(step => step.Words));
        Assert.Equal([null, null, "Bash", null], steps.Select(step => step.Tool));
    }

    [Fact]
    public async Task Works_a_step_back_from_when_it_ended_so_the_timeline_shows_when_it_ran()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:10.000"), "Bash", 4_000));

        // Claude Code writes its event once a Step is over, so a mark drawn at that moment would sit late.
        var step = Assert.Single(await studio.StepsIn(Morning));

        Assert.Equal(Moment(At(Yesterday, "09:00:06.000")), step.AtUtc);
        Assert.Equal(4_000, step.LengthMs);
    }

    [Fact]
    public async Task Marks_a_failed_tool_call_and_a_model_error_as_faults()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:10.000")),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:00:20.000")),
            SessionEvent.ModelFailed(Morning, At(Yesterday, "09:00:30.000")));

        var steps = await studio.StepsIn(Morning);

        Assert.Equal([false, true, true], steps.Select(step => step.Fault));
        Assert.Equal(["tool", "tool", "fault"], steps.Select(step => step.Kind));
        Assert.Equal([null, "ShellError", "RateLimited"], steps.Select(step => step.Words));
    }

    [Fact]
    public async Task Keeps_a_refusal_and_a_hook_block_out_of_the_faults()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Refused(Morning, At(Yesterday, "09:00:10.000")),
            SessionEvent.HookBlocked(Morning, At(Yesterday, "09:00:20.000")));

        // Somebody chose both, so a clean run still reads clean.
        var steps = await studio.StepsIn(Morning);

        Assert.Equal(["refused", "refused"], steps.Select(step => step.Kind));
        Assert.All(steps, step => Assert.False(step.Fault));
        Assert.Equal(["user_reject", "hook"], steps.Select(step => step.Words));
    }

    [Fact]
    public async Task Leaves_the_allowed_decision_off_the_timeline()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Allowed(Morning, At(Yesterday, "09:00:10.000")),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:12.000")));

        // The Tool call's own mark already covers it, so a second mark would read as two calls.
        Assert.Equal(["tool"], (await studio.StepsIn(Morning)).Select(step => step.Kind));
    }

    [Fact]
    public async Task Leaves_the_request_that_named_the_run_off_the_timeline()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:05.000"), "The build fix"));

        // Claude Code asked for the title itself, so it is no part of what was said.
        Assert.Equal(["prompt"], (await studio.StepsIn(Morning)).Select(step => step.Kind));
    }

    [Fact]
    public async Task Reads_only_the_run_that_was_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Prompted(Afternoon, At(Yesterday, "14:00:00.000"), "Write the docs"));

        Assert.Equal(["Fix the build"], (await studio.StepsIn(Morning)).Select(step => step.Words));
    }

    [Fact]
    public async Task Says_no_run_is_held_under_an_id_the_store_does_not_know()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        var answer = await studio.StepAnswer(Evening);

        // An empty timeline under a real run and one under a mistyped address must not look alike.
        Assert.Null(answer.Run);
        Assert.Empty(answer.Steps);
    }

    [Fact]
    public async Task Names_the_events_store_when_one_run_cannot_be_read()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        var answer = await studio.StepAnswer(Morning);

        Assert.Equal("unreachable", answer.Events.Kind);
        Assert.NotNull(answer.Events.Missing);
        Assert.Null(answer.Run);
        Assert.Empty(answer.Steps);
    }

    [Fact]
    public async Task Reads_a_run_that_holds_more_events_than_one_page_of_the_store()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Every(Evening, At(Yesterday, "09:00:00.000"), TimeSpan.FromSeconds(1), MoreEventsThanOnePageHolds));

        // A run cut at the end of a page would draw a timeline that stops before the run did.
        Assert.Equal(MoreEventsThanOnePageHolds, (await studio.StepsIn(Evening)).Count);
    }

    [Fact]
    public async Task Draws_the_steps_oldest_first()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Answered(Morning, At(Yesterday, "09:01:00.000"), "Built."));
        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        // The store answers stream by stream, and a timeline reads a run the way it ran.
        Assert.Equal(["Fix the build", "Built."], (await studio.StepsIn(Morning)).Select(step => step.Words));
    }

    [Fact]
    public async Task Reads_only_the_days_the_span_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(DaysBack(3), "09:00:00.000"), "The early words"),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "The later words"));

        var steps = await studio.StepsIn(Morning, $"?from={Written(Yesterday)}&to={Written(Yesterday)}");

        Assert.Equal(["The later words"], steps.Select(step => step.Words));
    }
}
