using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Watch.Skills;

public sealed partial class SkillEndpointsTests
{
    private static readonly string GrilledAt = At(Yesterday, "14:48:23.182");

    [Fact]
    public async Task Names_the_plugin_and_the_marketplace_a_skill_was_delivered_by()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated(
            "grilling",
            GrilledAt,
            Trigger: "claude-proactive",
            Source: "plugin",
            Plugin: "probekit",
            Marketplace: "privateprobe"));

        var origin = Assert.Single((await studio.SkillOn(Yesterday, "grilling")).Origins);

        Assert.Equal("probekit", origin.Plugin);
        Assert.Equal("privateprobe", origin.Marketplace);
    }

    [Fact]
    public async Task Leaves_a_plugin_and_marketplace_the_store_did_not_record_unnamed()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive", Source: "projectSettings"));

        var origin = Assert.Single((await studio.SkillOn(Yesterday, "grilling")).Origins);

        // A skill loaded from a folder has no plugin, so it stays empty rather than taking a stand-in name.
        Assert.Null(origin.Plugin);
        Assert.Null(origin.Marketplace);
    }

    [Fact]
    public async Task Joins_where_a_skill_came_from_to_what_it_spent_in_one_day()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated(
            "comment-sweep",
            At(DaysBack(5), "09:00:04.000"),
            Trigger: "claude-proactive",
            Source: "projectSettings"));
        await studio.Push(new ApiRequest(At(DaysBack(5), "09:00:10.000"), Skill: "comment-sweep", CostUsd: 0.12m));

        var swept = await studio.SkillOn(DaysBack(5), "comment-sweep");

        // What fired, from where, and what it cost belong in one row, not on two screens.
        Assert.Equal("projectSettings", Assert.Single(swept.Origins).Source);
        Assert.Equal(0.12m, swept.Spend?.Cost);
    }

    [Fact]
    public async Task Tells_two_skills_that_share_a_name_apart_by_where_they_came_from()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "14:48:23.100"), Source: "plugin", Plugin: "probekit", Marketplace: "privateprobe"),
            new SkillActivated("grilling", At(Yesterday, "14:50:00.000"), Source: "plugin", Plugin: "probekit", Marketplace: "skillworks"));

        var origins = (await studio.SkillOn(Yesterday, "grilling")).Origins;

        // One name, two skills: the count cannot tell them apart, and the provenance can.
        Assert.Equal(["privateprobe", "skillworks"], origins.Select(origin => origin.Marketplace));
    }

    [Fact]
    public async Task Reports_each_way_a_skill_was_delivered_once_however_often_it_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(Yesterday, "14:48:23.100"), Trigger: "claude-proactive", Source: "projectSettings"),
            new SkillActivated("grilling", At(Yesterday, "14:52:00.000"), Trigger: "claude-proactive", Source: "projectSettings"));

        Assert.Single((await studio.SkillOn(Yesterday, "grilling")).Origins);
    }

    [Fact]
    public async Task Reads_only_the_events_sent_to_its_own_tenant()
    {
        using var sent = new StudioHost();
        using var other = new StudioHost();

        await sent.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var elsewhere = await other.SkillAnswer();

        // One Loki serves many teams, and another tenant's Activations would be another team's skills.
        Assert.NotEmpty((await sent.SkillOn(Yesterday, "grilling")).Origins);
        Assert.Equal("quiet", elsewhere.Gap.Kind);
        Assert.Empty(elsewhere.Skills);
    }

    [Fact]
    public async Task Takes_where_a_skill_came_from_only_from_the_day_it_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", At(DaysBack(11), "23:59:59.999"), Trigger: "agent-preload"),
            new SkillActivated("grilling", At(DaysBack(10), "00:00:00.000"), Trigger: "claude-proactive"),
            new SkillActivated("grilling", At(DaysBack(10), "23:59:59.999"), Trigger: "user-slash"),
            new SkillActivated("grilling", At(DaysBack(9), "00:00:00.000"), Trigger: "nested-skill"));

        var grilling = await studio.SkillOn(DaysBack(10), "grilling", $"?from={Written(DaysBack(11))}&to={Written(DaysBack(9))}");

        // Whole UTC days, both ends taken in, or a day's figures would take in facts from the days either side.
        Assert.Equal(["claude-proactive", "user-slash"], grilling.Origins.Select(origin => origin.Trigger));
    }
}
