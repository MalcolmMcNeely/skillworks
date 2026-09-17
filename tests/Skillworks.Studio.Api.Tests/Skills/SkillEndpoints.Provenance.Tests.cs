using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    private const string GrilledAt = "2026-09-14T14:48:23.182Z";

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

        var origin = Assert.Single((await studio.SkillOn("2026-09-14", "grilling")).Origins);

        Assert.Equal("probekit", origin.Plugin);
        Assert.Equal("privateprobe", origin.Marketplace);
    }

    [Fact]
    public async Task Leaves_a_plugin_and_marketplace_the_store_did_not_record_unnamed()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive", Source: "projectSettings"));

        var origin = Assert.Single((await studio.SkillOn("2026-09-14", "grilling")).Origins);

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
            "2026-09-10T09:00:04.000Z",
            Trigger: "claude-proactive",
            Source: "projectSettings"));
        await studio.Push(new ApiRequest("2026-09-10T09:00:10.000Z", Skill: "comment-sweep", CostUsd: 0.12m));

        var swept = await studio.SkillOn("2026-09-10", "comment-sweep");

        // What fired, from where, and what it cost belong in one row, not on two screens.
        Assert.Equal("projectSettings", Assert.Single(swept.Origins).Source);
        Assert.Equal(0.12m, swept.Spend?.Cost);
    }

    [Fact]
    public async Task Tells_two_skills_that_share_a_name_apart_by_where_they_came_from()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T14:48:23.100Z", Source: "plugin", Plugin: "probekit", Marketplace: "privateprobe"),
            new SkillActivated("grilling", "2026-09-14T14:50:00.000Z", Source: "plugin", Plugin: "probekit", Marketplace: "skillworks"));

        var origins = (await studio.SkillOn("2026-09-14", "grilling")).Origins;

        // One name, two skills: the count cannot tell them apart, and the provenance can.
        Assert.Equal(["privateprobe", "skillworks"], origins.Select(origin => origin.Marketplace));
    }

    [Fact]
    public async Task Reports_each_way_a_skill_was_delivered_once_however_often_it_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T14:48:23.100Z", Trigger: "claude-proactive", Source: "projectSettings"),
            new SkillActivated("grilling", "2026-09-14T14:52:00.000Z", Trigger: "claude-proactive", Source: "projectSettings"));

        Assert.Single((await studio.SkillOn("2026-09-14", "grilling")).Origins);
    }

    [Fact]
    public async Task Reads_only_the_events_sent_to_its_own_tenant()
    {
        using var sent = new StudioHost();
        using var other = new StudioHost();

        await sent.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var elsewhere = await other.SkillAnswer();

        // One Loki serves many teams, and another tenant's Activations would be another team's skills.
        Assert.NotEmpty((await sent.SkillOn("2026-09-14", "grilling")).Origins);
        Assert.Equal("quiet", elsewhere.Gap.Kind);
        Assert.Empty(elsewhere.Skills);
    }

    [Fact]
    public async Task Takes_where_a_skill_came_from_only_from_the_day_it_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-04T23:59:59.999Z", Trigger: "agent-preload"),
            new SkillActivated("grilling", "2026-09-05T00:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-05T23:59:59.999Z", Trigger: "user-slash"),
            new SkillActivated("grilling", "2026-09-06T00:00:00.000Z", Trigger: "nested-skill"));

        var grilling = await studio.SkillOn("2026-09-05", "grilling", "?from=2026-09-04&to=2026-09-06");

        // Whole UTC days, both ends taken in, or a day's figures would take in facts from the days either side.
        Assert.Equal(["claude-proactive", "user-slash"], grilling.Origins.Select(origin => origin.Trigger));
    }
}
