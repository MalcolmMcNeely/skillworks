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
        Assert.True(turn.SkillKnown);
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
        await Traced(studio);

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
        await Traced(studio);

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
        await Traced(studio);

        var tool = (await studio.StepsIn(Morning))[0];

        Assert.Null(tool.Skill);
        Assert.False(tool.Unnamed);
        Assert.True(tool.SkillKnown);
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

    [Fact]
    public async Task Keeps_each_subagent_on_its_own_skill_when_their_events_interleave()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000"), request: "req_a") with { Skill = "tdd" },
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:01.000"), request: "req_b") with { Skill = "diagnosing-bugs" },
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:02.000"), "Bash", use: "toolu_a"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:03.000"), "Read", use: "toolu_b"));
        await studio.PushSpans(
            Morning,
            MainTrace,
            Asked("b11c0a9e00000011", "req_a", "agent-a"),
            Asked("b11c0a9e00000012", "req_b", "agent-b"),
            Ran("b11c0a9e00000013", "toolu_a", "agent-a"),
            Ran("b11c0a9e00000014", "toolu_b", "agent-b"));

        var steps = await studio.StepsIn(Morning);

        // The last Turn before the first Tool call is the other Subagent's, which is the mix-up a Span prevents.
        Assert.Equal(["tdd", "diagnosing-bugs", "tdd", "diagnosing-bugs"], steps.Select(step => step.Skill));
        Assert.All(steps, step => Assert.True(step.SkillKnown));
    }

    [Fact]
    public async Task Keeps_the_main_agent_on_its_own_skill_while_a_subagent_runs()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000"), request: "req_main") with { Skill = "implement" },
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:01.000"), request: "req_a") with { Skill = "tdd" },
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:02.000"), "Bash", use: "toolu_a"),
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:03.000"), "Read", use: "toolu_main"));
        await studio.PushSpans(
            Morning,
            MainTrace,
            Asked("b11c0a9e00000011", "req_main", null),
            Asked("b11c0a9e00000012", "req_a", "agent-a"),
            Ran("b11c0a9e00000013", "toolu_a", "agent-a"),
            Ran("b11c0a9e00000014", "toolu_main", null));

        var steps = await studio.StepsIn(Morning);

        Assert.Equal(["implement", "tdd", "tdd", "implement"], steps.Select(step => step.Skill));
    }

    [Fact]
    public async Task Says_a_tool_calls_skill_is_not_known_in_a_session_with_no_spans()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000")) with { Skill = "tdd" },
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:10.000")),
            SessionEvent.Refused(Morning, At(Yesterday, "09:00:20.000"), "Write"));

        var steps = await studio.StepsIn(Morning);

        // Neither No skill nor Unnamed, as both say something Claude Code told Studio and here it told nothing.
        Assert.Equal([true, false, false], steps.Select(step => step.SkillKnown));
        Assert.Equal(["tdd", null, null], steps.Select(step => step.Skill));
        Assert.All(steps, step => Assert.False(step.Unnamed));
    }

    [Fact]
    public async Task Says_a_tool_calls_skill_is_not_known_before_the_spans_land()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000")) with { Skill = "tdd" },
            SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:10.000")));
        await Traced(studio);

        var first = (await studio.StepLines(Morning)).First(line => StudioHost.KindOf(line) == "steps");

        Assert.Equal([true, false], first["steps"]!.AsArray().Select(step => (bool)step!["skillKnown"]!));
    }

    [Fact]
    public async Task Leaves_a_turns_skill_as_claude_code_named_it_once_the_spans_land()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:00.000"), request: "req_a") with { Skill = "tdd" },
            SessionEvent.Turned(Morning, At(Yesterday, "09:00:01.000"), request: "req_main") with { Skill = "third-party" });
        await studio.PushSpans(Morning, MainTrace, Asked("b11c0a9e00000011", "req_a", "agent-a"));

        var steps = await studio.StepsIn(Morning);

        Assert.Equal(["tdd", null], steps.Select(step => step.Skill));
        Assert.Equal([false, true], steps.Select(step => step.Unnamed));
    }

    // Any Span will do, as a Step no Span names an agent for is the main agent's once the Spans have landed.
    private static Task Traced(StudioHost studio) =>
        studio.PushSpans(Morning, MainTrace, Asked(TurnSpan, "req_main", null));
}
