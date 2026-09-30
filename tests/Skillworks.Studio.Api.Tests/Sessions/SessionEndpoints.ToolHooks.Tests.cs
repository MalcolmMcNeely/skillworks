using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Gives_a_tool_call_the_hooks_that_ran_before_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.HooksRan(Morning, At(Yesterday, "09:00:01.000"), "PreToolUse", "Bash", 2, 850),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), "Bash", 4_000));

        var call = await OnlyToolIn(studio);

        Assert.Equal(new HookRunRow { Count = 2, LengthMs = 850 }, call.HooksBefore);
    }

    [Fact]
    public async Task Gives_a_tool_call_the_hooks_that_ran_after_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), "Bash", 4_000),
            SessionEvent.HooksRan(Morning, At(Yesterday, "09:00:06.000"), "PostToolUse", "Bash", 1, 1_200));

        var call = await OnlyToolIn(studio);

        Assert.Equal(new HookRunRow { Count = 1, LengthMs = 1_200 }, call.HooksAfter);
    }

    [Fact]
    public async Task Gives_a_tool_call_the_hook_run_nearest_in_time_where_a_restart_numbered_two_the_same()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.HooksRan(Morning, At(Yesterday, "08:00:00.000"), "PreToolUse", "Bash", 3, 900) with { Sequence = "4" },
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.HooksRan(Morning, At(Yesterday, "09:00:01.000"), "PreToolUse", "Bash", 1, 120) with { Sequence = "4" },
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), "Bash", 4_000) with { Sequence = "5" },
            SessionEvent.HooksRan(Morning, At(Yesterday, "10:00:00.000"), "PreToolUse", "Bash", 5, 700) with { Sequence = "4" });

        var call = await OnlyToolIn(studio);

        Assert.Equal(new HookRunRow { Count = 1, LengthMs = 120 }, call.HooksBefore);
    }

    [Fact]
    public async Task Leaves_the_next_calls_hooks_out_of_a_tool_call_that_ran_none_after_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:00:05.000"), "Bash"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:10.000"), "Bash", 4_000),
            SessionEvent.HooksRan(Morning, At(Yesterday, "09:00:11.000"), "PostToolUse", "Bash", 1, 1_200));

        var answer = await studio.StepAnswer(Morning);
        var failed = answer.Steps.First(step => step.Kind == "tool");

        Assert.Null(answer.Tools[failed.Id].HooksAfter);
    }

    [Fact]
    public async Task Leaves_a_hook_run_of_another_tool_out_of_a_tool_calls_hooks()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.HooksRan(Morning, At(Yesterday, "09:00:01.000"), "PreToolUse", "Edit", 1, 300),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), "Bash", 4_000));

        var call = await OnlyToolIn(studio);

        Assert.Null(call.HooksBefore);
    }
}
