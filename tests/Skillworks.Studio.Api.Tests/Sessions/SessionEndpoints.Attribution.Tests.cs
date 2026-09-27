using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Names_the_skill_in_force_on_a_turn_step()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000"), 1_000, 0.25m) with { Skill = "tdd" });

        var turn = Assert.Single(await studio.StepsIn(Morning));

        Assert.Equal("tdd", turn.Skill);
        Assert.False(turn.Unnamed);
        Assert.Equal(0.25m, turn.Cost);
    }

    [Fact]
    public async Task Gives_a_tool_call_the_skill_of_the_turn_that_asked_for_it()
    {
        using var studio = new StudioHost();

        // Claude Code writes the skill on the Turn alone, and a Tool call runs after the Turn that asked for it.
        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000")) with { Skill = "tdd" },
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:10.000")),
            SessionEvent.Refused(Morning, At(Yesterday, "09:00:20.000"), "Write"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:01:00.000")) with { Skill = "diagnosing-bugs" },
            SessionEvent.ToolFailed(Morning, At(Yesterday, "09:01:10.000"), "Read"));

        var steps = await studio.StepsIn(Morning);

        Assert.Equal(
            ["tdd", "tdd", "tdd", "diagnosing-bugs", "diagnosing-bugs"],
            steps.Select(step => step.Skill));
    }

    [Fact]
    public async Task Tells_a_step_with_no_skill_apart_from_one_whose_skill_claude_code_will_not_name()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000")),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:10.000")),
            SessionEvent.Turned(Morning, At(Yesterday, "09:01:00.000")) with { Skill = "third-party" },
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:01:10.000")));

        var steps = await studio.StepsIn(Morning);

        // A skill was in force on the last two, so reading them as no skill would say the opposite of what happened.
        Assert.All(steps, step => Assert.Null(step.Skill));
        Assert.Equal([false, false, true, true], steps.Select(step => step.Unnamed));
    }

    [Fact]
    public async Task Gives_a_tool_call_no_turn_asked_for_no_skill()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:00.000")),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:10.000")) with { Skill = "tdd" });

        var tool = (await studio.StepsIn(Morning))[0];

        Assert.Null(tool.Skill);
        Assert.False(tool.Unnamed);
    }

    [Fact]
    public async Task Gives_a_prompt_and_an_answer_no_skill_and_no_cost()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"),
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:10.000"), 1_000, 0.25m) with { Skill = "tdd" },
            SessionEvent.Answered(Morning, At(Yesterday, "09:00:20.000"), "Done"));

        var steps = await studio.StepsIn(Morning);

        // Only a Turn and the Tool calls it asked for are spend, so nothing else is attributed to a skill.
        Assert.Equal([null, "tdd", null], steps.Select(step => step.Skill));
        Assert.Equal([0m, 0.25m, 0m], steps.Select(step => step.Cost));
    }
}
