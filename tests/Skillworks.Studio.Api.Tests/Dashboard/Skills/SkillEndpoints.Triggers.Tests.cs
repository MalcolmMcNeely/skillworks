using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Dashboard.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Counts_a_skill_s_Activations_by_what_set_it_off()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Trigger: "claude-proactive"),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000"), Trigger: "claude-proactive"),
            new SkillActivated("grilling", At(Yesterday, "09:10:00.000"), Trigger: "user-slash"),
            new SkillActivated("tdd", At(Yesterday, "09:20:00.000"), Trigger: "nested-skill"));

        var skills = await studio.SkillsOn(Yesterday, OnlyYesterday);

        Assert.Equal(
            [Fired("claude-proactive", 2), Fired("user-slash", 1)],
            skills.Single(skill => skill.Name == "grilling").Triggers);
        Assert.Equal([Fired("nested-skill", 1)], skills.Single(skill => skill.Name == "tdd").Triggers);
    }

    [Fact]
    public async Task Counts_one_trigger_once_however_many_ways_the_skill_reached_the_session()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Trigger: "claude-proactive", Source: "projectSettings"),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000"), Trigger: "claude-proactive", Source: "plugin", Plugin: "probekit"));

        var grilling = await studio.SkillOn(Yesterday, "grilling", OnlyYesterday);

        Assert.Equal([Fired("claude-proactive", 2)], grilling.Triggers);
    }

    [Fact]
    public async Task Counts_an_activation_whose_trigger_went_unsent_under_no_trigger()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000"), Trigger: "user-slash"));

        var grilling = await studio.SkillOn(Yesterday, "grilling", OnlyYesterday);

        // An older Claude Code sends no trigger, and folding those Activations into one of the four would invent a reading.
        Assert.Equal([Fired(null, 1), Fired("user-slash", 1)], grilling.Triggers);
    }

    [Fact]
    public async Task Counts_a_day_s_Activations_as_the_sum_of_its_triggers()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Trigger: "claude-proactive"),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000"), Trigger: "user-slash"),
            new SkillActivated("grilling", At(Yesterday, "09:10:00.000")));

        var grilling = await studio.SkillOn(Yesterday, "grilling", OnlyYesterday);

        // Two figures for one day that disagree would leave the developer unsure which to believe.
        Assert.Equal(grilling.Activations, grilling.Triggers.Sum(trigger => trigger.Activations));
    }

    [Fact]
    public async Task Counts_by_trigger_only_the_activations_the_filter_keeps()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000"), Trigger: "claude-proactive", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", At(Yesterday, "11:00:00.000"), Trigger: "user-slash", Owner: "acme", RepositoryName: "nu"));

        var grilling = await studio.SkillOn(Yesterday, "grilling", $"?from={Written(Yesterday)}&to={Written(Yesterday)}&repository=acme/nu");

        Assert.Equal([Fired("user-slash", 1)], grilling.Triggers);
    }

    [Fact]
    public async Task Gives_a_skill_that_spent_but_never_fired_no_triggers()
    {
        using var studio = new StudioHost();

        await studio.Push(new ApiRequest(At(Yesterday, "09:01:00.000"), Skill: "grilling", CostUsd: 0.2m));

        var grilling = await studio.SkillOn(Yesterday, "grilling", OnlyYesterday);

        Assert.Empty(grilling.Triggers);
    }

    private static TriggerRow Fired(string? trigger, int activations) =>
        new() { Trigger = trigger, Activations = activations };
}
