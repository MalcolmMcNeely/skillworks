using System.Globalization;
using System.Net;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    private const string GrilledAt = "2026-09-02T14:48:23.182Z";

    [Fact]
    public async Task Names_the_plugin_and_the_marketplace_a_skill_was_delivered_by()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.Push(new SkillActivated(
            "grilling",
            GrilledAt,
            Trigger: "claude-proactive",
            Source: "plugin",
            Plugin: "probekit",
            Marketplace: "privateprobe"));

        var origin = Assert.Single((await studio.Skill("grilling")).Origins);

        Assert.Equal("probekit", origin.Plugin);
        Assert.Equal("privateprobe", origin.Marketplace);
    }

    [Fact]
    public async Task Leaves_a_plugin_and_marketplace_the_store_did_not_record_unnamed()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive", Source: "projectSettings"));

        var origin = Assert.Single((await studio.Skill("grilling")).Origins);

        // A skill loaded from a folder has no plugin, so it stays empty rather than taking a stand-in name.
        Assert.Null(origin.Plugin);
        Assert.Null(origin.Marketplace);
    }

    [Fact]
    public async Task Joins_where_a_skill_came_from_to_what_it_spent_in_one_answer()
    {
        using var studio = new StudioHost(StudioHost.Fixture("costly"));

        await studio.Push(new SkillActivated(
            "comment-sweep",
            "2026-09-10T09:00:04.000Z",
            Trigger: "claude-proactive",
            Source: "plugin",
            Plugin: "probekit",
            Marketplace: "privateprobe"));

        var swept = await studio.Skill("comment-sweep");

        // What fired, from where, and what it cost, in one row, is the join the two stores exist to make.
        Assert.Equal("privateprobe", Assert.Single(swept.Origins).Marketplace);
        Assert.True(swept.Spend.Cost > 0m);
    }

    [Fact]
    public async Task Tells_two_skills_that_share_a_name_apart_by_where_they_came_from()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.Push(
            new SkillActivated("grilling", "2026-09-02T14:48:23.100Z", Source: "plugin", Plugin: "probekit", Marketplace: "privateprobe"),
            new SkillActivated("grilling", "2026-09-02T14:50:00.000Z", Source: "plugin", Plugin: "probekit", Marketplace: "skillworks"));

        var origins = (await studio.Skill("grilling")).Origins;

        // One name, two skills: the count cannot tell them apart, and the provenance can.
        Assert.Equal(["privateprobe", "skillworks"], origins.Select(origin => origin.Marketplace));
    }

    [Fact]
    public async Task Reports_each_way_a_skill_was_delivered_once_however_often_it_fired()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.Push(
            new SkillActivated("grilling", "2026-09-02T14:48:23.100Z", Trigger: "claude-proactive", Source: "projectSettings"),
            new SkillActivated("grilling", "2026-09-02T14:52:00.000Z", Trigger: "claude-proactive", Source: "projectSettings"));

        Assert.Single((await studio.Skill("grilling")).Origins);
    }

    [Fact]
    public async Task Reads_only_the_events_sent_to_its_own_tenant()
    {
        using var sent = new StudioHost(StudioHost.Fixture("ordinary"));
        using var other = new StudioHost(StudioHost.Fixture("ordinary"));

        await sent.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var elsewhere = await other.SkillTable();

        // One Loki serves many teams, and another tenant's origins would be another team's skills.
        Assert.NotEmpty((await sent.Skill("grilling")).Origins);
        Assert.Equal("quiet", elsewhere.Provenance.Gap);
        Assert.Empty(Assert.Single(elsewhere.Skills).Origins);
    }

    [Fact]
    public async Task Says_the_events_store_could_not_be_read_rather_than_that_nothing_fired()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), events: events);

        var answer = await studio.SkillTable();
        var grilling = Assert.Single(answer.Skills);

        Assert.Equal("unreachable", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);

        // The transcripts stand on their own, so the count and the cost remain and only the provenance is gone.
        Assert.Equal(1, grilling.Activations);
        Assert.Empty(grilling.Origins);
    }

    [Fact]
    public async Task Reports_an_events_store_that_answers_badly_as_unreachable_rather_than_as_quiet()
    {
        using var events = BrokenEventsStore.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), events: events);

        var answer = await studio.SkillTable();

        // An events store that is up and unhappy is an outage, or missing provenance would read as none.
        Assert.Equal("unreachable", answer.Provenance.Gap);
        Assert.Contains("502", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Labels_a_period_the_events_store_holds_nothing_for_as_missing()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        var answer = await studio.SkillTable();

        // Nothing is broken and nothing was recorded, and saying so tells "none" from "not recorded".
        Assert.Equal("quiet", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);
        Assert.Empty(Assert.Single(answer.Skills).Origins);
    }

    [Fact]
    public async Task Says_telemetry_was_never_switched_on_rather_than_that_the_period_was_quiet()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), emitting: false);

        var answer = await studio.SkillTable();

        // Empty because nothing was ever sent, and a reader told "quiet" would look for a fault that is not there.
        Assert.Equal("telemetryOff", answer.Provenance.Gap);
        Assert.Contains("Telemetry panel", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Tells_a_store_that_is_down_apart_from_telemetry_that_was_never_switched_on()
    {
        using var down = BrokenEventsStore.Down();
        using var broken = new StudioHost(StudioHost.Fixture("ordinary"), events: down, emitting: true);
        using var off = new StudioHost(StudioHost.Fixture("ordinary"), emitting: false);

        var outage = (await broken.SkillTable()).Provenance;
        var never = (await off.SkillTable()).Provenance;

        // Both answers are empty, and a caller that only counted events could not tell the two problems apart.
        Assert.Equal("unreachable", outage.Gap);
        Assert.Equal("telemetryOff", never.Gap);
        Assert.NotEqual(outage.Missing, never.Missing);
    }

    [Fact]
    public async Task Says_telemetry_is_off_even_where_the_store_has_events_from_before_it_was()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), emitting: false);

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var answer = await studio.SkillTable();

        // The earlier origins are real, but nothing has reached the events store since the switch went off.
        Assert.Equal("telemetryOff", answer.Provenance.Gap);
        Assert.Contains("Telemetry panel", answer.Provenance.Missing ?? "");
        Assert.NotEmpty(Assert.Single(answer.Skills).Origins);
    }

    [Fact]
    public async Task Says_it_cannot_tell_whether_telemetry_was_on_rather_than_saying_it_was_off()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), settings: "{ not json");

        var answer = await studio.SkillTable();

        // Not "off": that would tell a developer to flip a switch Studio has refused to touch.
        Assert.Equal("telemetryUnknown", answer.Provenance.Gap);
        Assert.Contains("cannot read", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Says_when_a_period_held_more_events_than_it_could_read_at_once()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), maxEvents: 2);

        await studio.Push(
            new SkillActivated("grilling", "2026-09-02T14:48:23.100Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-02T14:50:00.000Z", Trigger: "user-slash"));

        var answer = await studio.SkillTable();

        // A full answer and a cut one look the same from here, so a full one is reported as cut.
        Assert.Equal("truncated", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);
        Assert.Equal(2, Assert.Single(answer.Skills).Origins.Length);
    }

    [Fact]
    public async Task Says_nothing_is_missing_when_the_store_answered_with_events()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var answer = await studio.SkillTable();

        Assert.Equal("complete", answer.Provenance.Gap);
        Assert.Null(answer.Provenance.Missing);
    }

    [Fact]
    public async Task Takes_where_a_skill_came_from_only_from_the_whole_days_the_filter_names()
    {
        using var studio = new StudioHost(StudioHost.Fixture("filtered"));

        await studio.Push(
            new SkillActivated("grilling", "2026-09-04T23:59:59.999Z", Trigger: "agent-preload"),
            new SkillActivated("grilling", "2026-09-05T00:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-05T23:59:59.999Z", Trigger: "user-slash"),
            new SkillActivated("grilling", "2026-09-06T00:00:00.000Z", Trigger: "nested-skill"));

        var grilling = await studio.Skill("grilling", "?from=2026-09-05&to=2026-09-05");

        // Whole UTC days, both ends taken in, or a filtered screen would get unfiltered facts from the events store.
        Assert.Equal(["claude-proactive", "user-slash"], grilling.Origins.Select(origin => origin.Trigger));
    }

    [Fact]
    public async Task Says_how_far_back_the_provenance_it_is_showing_reaches()
    {
        using var studio = new StudioHost(StudioHost.Fixture("filtered"));

        var answer = await studio.SkillTable("?from=2026-09-05&to=2026-09-05");

        // A gap read as a fact is provenance's likeliest failure, so every answer names the earliest moment it covers.
        Assert.Equal(
            DateTimeOffset.Parse("2026-09-05T00:00:00Z", CultureInfo.InvariantCulture),
            answer.Provenance.SinceUtc);
    }
}
