using System.Globalization;
using System.Net;
using System.Web;

namespace Skillworks.Studio.Api.Tests;

/// <summary>
/// Where a skill came from and what set it off. Transcripts carry neither, so this is the whole
/// reason the events store exists, and every answer here is the two stores joined on skill name
/// and moment.
/// </summary>
public sealed class ProvenanceEndpointTests
{
    /// <summary>The one firing in the ordinary fixture, and the moment the transcript gives it.</summary>
    private const string Grilling = "toolu_01EAt7jnkYt1D63phjpVUBqL";

    private const string GrilledAt = "2026-09-02T14:48:23.182Z";

    [Fact]
    public async Task Says_whether_claude_chose_a_skill_or_a_developer_typed_it()
    {
        using var events = Events.Holding(
            new Event("grilling", "2026-09-02T14:48:23.100Z", Trigger: "user-slash", Source: "userSettings"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var opened = await studio.Activation(Grilling);

        // Verbatim, as the store recorded it. The words a reader sees are the screen's business;
        // what the API owes is the fact underneath them.
        Assert.Equal("user-slash", opened.Origin?.Trigger);
        Assert.Equal("userSettings", opened.Origin?.Source);
    }

    [Fact]
    public async Task Says_which_trigger_set_off_each_firing_in_the_list()
    {
        using var events = Events.Holding(
            new Event("grilling", GrilledAt, Trigger: "claude-proactive"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var listed = Assert.Single(await studio.Activations());

        Assert.Equal("claude-proactive", listed.Origin?.Trigger);
    }

    [Fact]
    public async Task Names_the_plugin_and_the_marketplace_a_skill_was_delivered_by()
    {
        using var events = Events.Holding(new Event(
            "grilling",
            GrilledAt,
            Trigger: "claude-proactive",
            Source: "plugin",
            Plugin: "probekit",
            Marketplace: "privateprobe"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var origin = Assert.Single((await studio.Skill("grilling")).Origins);

        Assert.Equal("probekit", origin.Plugin);
        Assert.Equal("privateprobe", origin.Marketplace);
    }

    [Fact]
    public async Task Leaves_a_plugin_and_marketplace_the_store_did_not_record_unnamed()
    {
        using var events = Events.Holding(
            new Event("grilling", GrilledAt, Trigger: "claude-proactive", Source: "projectSettings"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var origin = Assert.Single((await studio.Skill("grilling")).Origins);

        // A skill loaded from a folder has no plugin behind it. That is a fact about the skill, so
        // it is left empty rather than filled in with a stand-in name.
        Assert.Null(origin.Plugin);
        Assert.Null(origin.Marketplace);
    }

    [Fact]
    public async Task Joins_where_a_skill_came_from_to_what_it_spent_in_one_answer()
    {
        using var events = Events.Holding(new Event(
            "comment-sweep",
            "2026-09-10T09:00:04.000Z",
            Trigger: "claude-proactive",
            Source: "plugin",
            Plugin: "probekit",
            Marketplace: "privateprobe"));
        using var studio = new Studio(Studio.Fixture("costly"), events: events);

        var swept = await studio.Skill("comment-sweep");

        // One row, both halves: what fired, from where, and what it cost. That is the join the two
        // stores exist to make.
        Assert.Equal("privateprobe", Assert.Single(swept.Origins).Marketplace);
        Assert.True(swept.Spend.Cost > 0m);
    }

    [Fact]
    public async Task Tells_two_skills_that_share_a_name_apart_by_where_they_came_from()
    {
        using var events = Events.Holding(
            new Event("grilling", "2026-09-02T14:48:23.100Z", Source: "plugin", Plugin: "probekit", Marketplace: "privateprobe"),
            new Event("grilling", "2026-09-02T14:50:00.000Z", Source: "plugin", Plugin: "probekit", Marketplace: "skillworks"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var origins = (await studio.Skill("grilling")).Origins;

        // One name, two skills. The count cannot tell them apart and the provenance can, which is
        // the point of keeping both.
        Assert.Equal(["privateprobe", "skillworks"], origins.Select(origin => origin.Marketplace));
    }

    [Fact]
    public async Task Reports_each_way_a_skill_was_delivered_once_however_often_it_fired()
    {
        using var events = Events.Holding(
            new Event("grilling", "2026-09-02T14:48:23.100Z", Trigger: "claude-proactive", Source: "projectSettings"),
            new Event("grilling", "2026-09-02T14:52:00.000Z", Trigger: "claude-proactive", Source: "projectSettings"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        Assert.Single((await studio.Skill("grilling")).Origins);
    }

    [Fact]
    public async Task Says_the_events_store_could_not_be_read_rather_than_that_nothing_fired()
    {
        using var events = Events.Down();
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var answer = await studio.SkillTable();
        var grilling = Assert.Single(answer.Skills);

        Assert.Equal("unreachable", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);

        // The transcript half is the durable record and stands on its own, so the count and the
        // cost are still there. Only the provenance is gone.
        Assert.Equal(1, grilling.Activations);
        Assert.Empty(grilling.Origins);
    }

    [Fact]
    public async Task Reports_an_events_store_that_answers_badly_as_unreachable_rather_than_as_quiet()
    {
        using var events = Events.Failing(HttpStatusCode.BadGateway);
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var answer = await studio.SkillTable();

        // A store that is up and unhappy is an outage. Reading it as silence would report the
        // provenance as genuinely absent, which is the one thing this half must never do.
        Assert.Equal("unreachable", answer.Provenance.Gap);
        Assert.Contains("502", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Labels_a_period_the_events_store_holds_nothing_for_as_missing()
    {
        using var events = Events.Holding();
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var answer = await studio.SkillTable();

        // The store answered and telemetry is on, so nothing is broken, and there is still no
        // provenance for this period. Saying so is the difference between "not recorded" and "none".
        Assert.Equal("quiet", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);
        Assert.Empty(Assert.Single(answer.Skills).Origins);
    }

    [Fact]
    public async Task Says_telemetry_was_never_switched_on_rather_than_that_the_period_was_quiet()
    {
        using var events = Events.Holding();
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events, emitting: false);

        var answer = await studio.SkillTable();

        // The store is up and empty, and the reason is that nothing was ever sent to it. A reader
        // told the period was quiet would go looking for a fault that is not there.
        Assert.Equal("telemetryOff", answer.Provenance.Gap);
        Assert.Contains("Telemetry panel", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Tells_a_store_that_is_down_apart_from_telemetry_that_was_never_switched_on()
    {
        using var down = Events.Down();
        using var quiet = Events.Holding();
        using var broken = new Studio(Studio.Fixture("ordinary"), events: down, emitting: true);
        using var off = new Studio(Studio.Fixture("ordinary"), events: quiet, emitting: false);

        var outage = (await broken.SkillTable()).Provenance;
        var never = (await off.SkillTable()).Provenance;

        // Two empty answers, two different problems, two different things to do about them. A
        // caller that only counted the events it got back could not tell these apart at all.
        Assert.Equal("unreachable", outage.Gap);
        Assert.Equal("telemetryOff", never.Gap);
        Assert.NotEqual(outage.Missing, never.Missing);
    }

    [Fact]
    public async Task Says_telemetry_is_off_even_where_the_store_has_events_from_before_it_was()
    {
        using var events = Events.Holding(new Event("grilling", GrilledAt, Trigger: "claude-proactive"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events, emitting: false);

        var answer = await studio.SkillTable();

        // The origins on screen are real and were recorded earlier. The period runs up to now, and
        // nothing has reached the store since the switch went off, so a whole-looking answer would
        // be read as covering a stretch it does not.
        Assert.Equal("telemetryOff", answer.Provenance.Gap);
        Assert.Contains("Telemetry panel", answer.Provenance.Missing ?? "");
        Assert.NotEmpty(Assert.Single(answer.Skills).Origins);
    }

    [Fact]
    public async Task Says_it_cannot_tell_whether_telemetry_was_on_rather_than_saying_it_was_off()
    {
        using var events = Events.Holding();
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events, settings: "{ not json");

        var answer = await studio.SkillTable();

        // Studio refuses to write a settings file it could not parse, and reports one as not
        // emitting so it never writes it by accident. Repeating that on a screen would tell a
        // developer to flip a switch Studio has already refused to touch.
        Assert.Equal("telemetryUnknown", answer.Provenance.Gap);
        Assert.Contains("cannot read", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Says_telemetry_is_off_beside_one_firing_as_well_as_beside_the_table()
    {
        using var events = Events.Holding();
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events, emitting: false);

        var opened = await studio.OpenActivation(Grilling);

        // The same question asked of one firing. A detail page that stayed silent would leave the
        // empty trigger beside it to be read as "Claude did not choose this one".
        Assert.Equal("telemetryOff", opened.Provenance.Gap);
        Assert.Null(opened.Activation.Origin);
    }

    [Fact]
    public async Task Says_when_a_period_held_more_events_than_it_could_read_at_once()
    {
        using var events = Events.Holding(
            new Event("grilling", "2026-09-02T14:48:23.100Z", Trigger: "claude-proactive"),
            new Event("grilling", "2026-09-02T14:50:00.000Z", Trigger: "user-slash"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events, maxEvents: 2);

        var answer = await studio.SkillTable();

        // A full answer and a cut one look the same from here, so a full one is reported as cut.
        // The origins on screen are real; what is not said is whether they are all of them.
        Assert.Equal("truncated", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);
        Assert.Equal(2, Assert.Single(answer.Skills).Origins.Length);
    }

    [Fact]
    public async Task Says_nothing_is_missing_when_the_store_answered_with_events()
    {
        using var events = Events.Holding(new Event("grilling", GrilledAt, Trigger: "claude-proactive"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var answer = await studio.SkillTable();

        Assert.Equal("complete", answer.Provenance.Gap);
        Assert.Null(answer.Provenance.Missing);
    }

    [Fact]
    public async Task Leaves_a_firing_with_no_event_near_it_without_an_origin()
    {
        using var events = Events.Holding(new Event("grilling", "2026-09-02T11:00:00.000Z", Trigger: "user-slash"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var opened = await studio.OpenActivation(Grilling);

        // The store is up, telemetry is on and it holds a grilling hours away from this one. So the
        // answer is whole: this firing has no origin because none was recorded near it, and a join
        // on name alone would have handed it somebody else's trigger.
        Assert.Equal("complete", opened.Provenance.Gap);
        Assert.Null(opened.Activation.Origin);
    }

    [Fact]
    public async Task Takes_the_event_nearest_a_firing_when_a_skill_fired_more_than_once()
    {
        using var events = Events.Holding(
            new Event("grilling", "2026-09-02T14:48:23.100Z", Trigger: "claude-proactive"),
            new Event("grilling", "2026-09-02T14:49:30.000Z", Trigger: "user-slash"));
        using var studio = new Studio(Studio.Fixture("ordinary"), events: events);

        var opened = await studio.Activation(Grilling);

        Assert.Equal("claude-proactive", opened.Origin?.Trigger);
    }

    [Fact]
    public async Task Asks_the_events_store_for_the_skill_events_of_the_period_the_filter_names()
    {
        using var events = Events.Holding();
        using var studio = new Studio(Studio.Fixture("filtered"), events: events);

        await studio.SkillTable("?from=2026-09-05&to=2026-09-05");

        var asked = HttpUtility.ParseQueryString(events.LastAsked!.Query);

        Assert.Contains("skill_activated", asked["query"] ?? "");

        // Whole UTC days, both ends taken in, exactly as every other view narrows. A store asked
        // for a wider period than the table would answer a filtered screen with unfiltered facts.
        Assert.Equal(Nanoseconds("2026-09-05T00:00:00Z"), asked["start"]);
        Assert.Equal(Nanoseconds("2026-09-06T00:00:00Z"), asked["end"]);
    }

    [Fact]
    public async Task Says_how_far_back_the_provenance_it_is_showing_reaches()
    {
        using var events = Events.Holding();
        using var studio = new Studio(Studio.Fixture("filtered"), events: events);

        var answer = await studio.SkillTable("?from=2026-09-05&to=2026-09-05");

        // A gap read as a fact is the failure this half is most prone to, so every answer names
        // the earliest moment it covers.
        Assert.Equal(
            DateTimeOffset.Parse("2026-09-05T00:00:00Z", CultureInfo.InvariantCulture),
            answer.Provenance.SinceUtc);
    }

    private static string Nanoseconds(string moment) =>
        (DateTimeOffset.Parse(moment, CultureInfo.InvariantCulture).ToUnixTimeMilliseconds() * 1_000_000)
        .ToString(CultureInfo.InvariantCulture);
}
