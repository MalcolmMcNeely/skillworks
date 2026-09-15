using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Counts_a_skill_s_Activations_by_what_set_it_off()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z", Trigger: "user-slash"),
            new SkillActivated("tdd", "2026-09-14T09:20:00.000Z", Trigger: "nested-skill"));

        var skills = await studio.SkillsOn("2026-09-14", OnlyTheFourteenth);

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
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Trigger: "claude-proactive", Source: "projectSettings"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Trigger: "claude-proactive", Source: "plugin", Plugin: "probekit"));

        var grilling = await studio.SkillOn("2026-09-14", "grilling", OnlyTheFourteenth);

        Assert.Equal([Fired("claude-proactive", 2)], grilling.Triggers);
    }

    [Fact]
    public async Task Counts_a_firing_whose_trigger_went_unsent_under_no_trigger()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Trigger: "user-slash"));

        var grilling = await studio.SkillOn("2026-09-14", "grilling", OnlyTheFourteenth);

        // An older Claude Code sends no trigger, and folding those firings into one of the four would invent a reading.
        Assert.Equal([Fired(null, 1), Fired("user-slash", 1)], grilling.Triggers);
    }

    [Fact]
    public async Task Counts_a_day_s_Activations_as_the_sum_of_its_triggers()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", Trigger: "user-slash"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z"));

        var grilling = await studio.SkillOn("2026-09-14", "grilling", OnlyTheFourteenth);

        // Two figures for one day that disagree would leave the developer unsure which to believe.
        Assert.Equal(grilling.Activations, grilling.Triggers.Sum(trigger => trigger.Activations));
    }

    [Fact]
    public async Task Counts_by_trigger_only_the_firings_the_filter_keeps()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Trigger: "claude-proactive", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-14T11:00:00.000Z", Trigger: "user-slash", Owner: "acme", RepositoryName: "nu"));

        var grilling = await studio.SkillOn("2026-09-14", "grilling", "?from=2026-09-14&to=2026-09-14&repository=acme/nu");

        Assert.Equal([Fired("user-slash", 1)], grilling.Triggers);
    }

    [Fact]
    public async Task Gives_a_skill_that_spent_but_never_fired_no_triggers()
    {
        using var studio = new StudioHost();

        await studio.Push(new ApiRequest("2026-09-14T09:01:00.000Z", Skill: "grilling", CostUsd: 0.2m));

        var grilling = await studio.SkillOn("2026-09-14", "grilling", OnlyTheFourteenth);

        Assert.Empty(grilling.Triggers);
    }

    private static TriggerRow Fired(string? trigger, int activations) =>
        new() { Trigger = trigger, Activations = activations };
}
