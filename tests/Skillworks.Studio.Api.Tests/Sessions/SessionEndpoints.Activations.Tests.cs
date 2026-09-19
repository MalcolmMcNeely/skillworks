using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Answers_one_run_with_lines_that_hold_only_what_the_activations_read()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", At(Yesterday, "09:00:00.000")));

        var page = await studio.StepLine("activations", Morning);

        Assert.Equal(["activations", "kind"], StudioHost.Fields(page));
        Assert.Equal(["atUtc", "followedMs", "id", "skill", "trigger"], StudioHost.Fields(page["activations"]?[0]));
    }

    [Fact]
    public async Task Lists_the_activations_of_a_run_in_order_with_the_skill_and_the_time()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("implement", At(Yesterday, "09:00:00.000")),
            Fired("tdd", At(Yesterday, "09:05:00.000")),
            Fired("comment-sweep", At(Yesterday, "09:20:00.000")));

        var activations = await studio.ActivationsIn(Morning);

        Assert.Equal(["implement", "tdd", "comment-sweep"], activations.Select(activation => activation.Skill));
        Assert.Equal(Moment(At(Yesterday, "09:05:00.000")), activations[1].AtUtc);
    }

    [Fact]
    public async Task Runs_an_activation_up_to_the_skill_that_fired_next()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("implement", At(Yesterday, "09:00:00.000")),
            Fired("tdd", At(Yesterday, "09:05:00.000")));
        await studio.Push(SessionEvent.ToolRan(Morning, At(Yesterday, "09:09:00.000")));

        Assert.Equal((long)TimeSpan.FromMinutes(5).TotalMilliseconds, (await studio.ActivationsIn(Morning))[0].FollowedMs);
    }

    [Fact]
    public async Task Runs_the_last_activation_up_to_the_end_of_the_run()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", At(Yesterday, "09:00:00.000")));
        await studio.Push(SessionEvent.Answered(Morning, At(Yesterday, "09:30:00.000"), "Done."));

        Assert.Equal(
            (long)TimeSpan.FromMinutes(30).TotalMilliseconds,
            Assert.Single(await studio.ActivationsIn(Morning)).FollowedMs);
    }

    [Fact]
    public async Task Says_how_an_activation_was_set_off()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", At(Yesterday, "09:00:00.000")) with { Trigger = "user-slash" });

        Assert.Equal("user-slash", Assert.Single(await studio.ActivationsIn(Morning)).Trigger);
    }

    [Fact]
    public async Task Gives_each_activation_an_identity_of_its_own()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", At(Yesterday, "09:00:00.000")),
            Fired("tdd", At(Yesterday, "09:05:00.000")));

        var activations = await studio.ActivationsIn(Morning);

        Assert.Equal(2, activations.Select(activation => activation.Id).Distinct().Count());
    }

    [Fact]
    public async Task Finds_no_activation_in_a_run_no_skill_fired_in()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"));

        Assert.Empty(await studio.ActivationsIn(Morning));
    }

    [Fact]
    public async Task Reads_the_activations_of_the_run_that_was_asked_for_alone()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", At(Yesterday, "09:00:00.000")),
            new SkillActivated("comment-sweep", At(Yesterday, "14:00:00.000")) { Session = Afternoon });

        Assert.Equal(["tdd"], (await studio.ActivationsIn(Morning)).Select(activation => activation.Skill));
    }

    [Fact]
    public async Task Answers_no_activations_when_one_run_cannot_be_read()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        Assert.Empty(await studio.ActivationsIn(Morning));
    }

    private static SkillActivated Fired(string skill, string at) => new(skill, at) { Session = Morning };
}
