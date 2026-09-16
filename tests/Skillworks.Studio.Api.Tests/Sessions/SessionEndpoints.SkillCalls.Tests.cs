using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Answers_one_run_with_lines_that_hold_only_what_the_skill_calls_read()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", "2026-09-14T09:00:00.000Z"));

        var page = await studio.StepLine("skillCalls", Morning);

        Assert.Equal(["kind", "skillCalls"], StudioHost.Fields(page));
        Assert.Equal(["atUtc", "followedMs", "id", "skill", "trigger"], StudioHost.Fields(page["skillCalls"]?[0]));
    }

    [Fact]
    public async Task Lists_the_skill_calls_of_a_run_in_order_with_the_skill_and_the_time()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("implement", "2026-09-14T09:00:00.000Z"),
            Fired("tdd", "2026-09-14T09:05:00.000Z"),
            Fired("comment-sweep", "2026-09-14T09:20:00.000Z"));

        var calls = await studio.SkillCallsIn(Morning);

        Assert.Equal(["implement", "tdd", "comment-sweep"], calls.Select(call => call.Skill));
        Assert.Equal(Moment("2026-09-14T09:05:00.000Z"), calls[1].AtUtc);
    }

    [Fact]
    public async Task Runs_a_skill_call_up_to_the_skill_that_fired_next()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("implement", "2026-09-14T09:00:00.000Z"),
            Fired("tdd", "2026-09-14T09:05:00.000Z"));
        await studio.Push(SessionEvent.ToolRan(Morning, "2026-09-14T09:09:00.000Z"));

        Assert.Equal((long)TimeSpan.FromMinutes(5).TotalMilliseconds, (await studio.SkillCallsIn(Morning))[0].FollowedMs);
    }

    [Fact]
    public async Task Runs_the_last_skill_call_up_to_the_end_of_the_run()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", "2026-09-14T09:00:00.000Z"));
        await studio.Push(SessionEvent.Answered(Morning, "2026-09-14T09:30:00.000Z", "Done."));

        Assert.Equal(
            (long)TimeSpan.FromMinutes(30).TotalMilliseconds,
            Assert.Single(await studio.SkillCallsIn(Morning)).FollowedMs);
    }

    [Fact]
    public async Task Says_how_a_skill_call_was_set_off()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", "2026-09-14T09:00:00.000Z") with { Trigger = "user-slash" });

        Assert.Equal("user-slash", Assert.Single(await studio.SkillCallsIn(Morning)).Trigger);
    }

    [Fact]
    public async Task Gives_each_skill_call_an_identity_of_its_own()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-14T09:00:00.000Z"),
            Fired("tdd", "2026-09-14T09:05:00.000Z"));

        var calls = await studio.SkillCallsIn(Morning);

        Assert.Equal(2, calls.Select(call => call.Id).Distinct().Count());
    }

    [Fact]
    public async Task Finds_no_skill_call_in_a_run_no_skill_fired_in()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, "2026-09-14T09:00:00.000Z", "Fix the build"));

        Assert.Empty(await studio.SkillCallsIn(Morning));
    }

    [Fact]
    public async Task Reads_the_skill_calls_of_the_run_that_was_asked_for_alone()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("comment-sweep", "2026-09-14T14:00:00.000Z") { Session = Afternoon });

        Assert.Equal(["tdd"], (await studio.SkillCallsIn(Morning)).Select(call => call.Skill));
    }

    [Fact]
    public async Task Answers_no_skill_calls_when_one_run_cannot_be_read()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        Assert.Empty(await studio.SkillCallsIn(Morning));
    }

    private static SkillActivated Fired(string skill, string at) => new(skill, at) { Session = Morning };
}
