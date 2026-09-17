using System.Net;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Ends_with_no_day_and_the_unreachable_Gap_when_the_store_cannot_be_read_from_the_start()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(StudioHost.Catalogue(), events: events);

        var answer = await studio.SkillAnswer();

        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.NotNull(answer.Gap.Missing);
        Assert.Empty(answer.Days);

        // The catalogue still lists its skills, and the Gap is what says their zeros are not known.
        Assert.NotEmpty(answer.Head.CatalogueSkills);
    }

    [Fact]
    public async Task Reports_an_events_store_that_answers_badly_as_unreachable_rather_than_as_quiet()
    {
        using var events = BrokenEventsStore.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(events: events);

        var answer = await studio.SkillAnswer();

        // An events store that is up and unhappy is an outage, or missing activations would read as none.
        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.Contains("502", answer.Gap.Missing ?? "");
    }

    [Fact]
    public async Task Labels_a_period_the_events_store_holds_nothing_for_as_missing()
    {
        using var studio = new StudioHost();

        var answer = await studio.SkillAnswer();

        // Nothing is broken and nothing was recorded, and saying so tells "none" from "not recorded".
        Assert.Equal("quiet", answer.Gap.Kind);
        Assert.NotNull(answer.Gap.Missing);
        Assert.Empty(answer.Skills);
    }

    [Fact]
    public async Task Says_nothing_is_missing_when_only_the_filter_matched_nothing()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", GrilledAt, Owner: "acme", RepositoryName: "xi"));

        var elsewhere = await studio.SkillAnswer("?repository=acme/nu");
        var unfired = await studio.SkillAnswer("?skill=tdd");

        // The store holds Activations for these days, so "quiet" would send a reader looking for a telemetry fault.
        Assert.Empty(elsewhere.Skills);
        Assert.Equal("complete", elsewhere.Gap.Kind);
        Assert.Empty(unfired.Skills);
        Assert.Equal("complete", unfired.Gap.Kind);
    }

    [Fact]
    public async Task Says_telemetry_was_never_switched_on_rather_than_that_the_period_was_quiet()
    {
        using var studio = new StudioHost(emitting: false);

        var answer = await studio.SkillAnswer();

        // Empty because nothing was ever sent, and a reader told "quiet" would look for a fault that is not there.
        Assert.Equal("telemetryOff", answer.Gap.Kind);
        Assert.Contains("Telemetry switch", answer.Gap.Missing ?? "");
    }

    [Fact]
    public async Task Tells_a_store_that_is_down_apart_from_telemetry_that_was_never_switched_on()
    {
        using var down = BrokenEventsStore.Down();
        using var broken = new StudioHost(events: down, emitting: true);
        using var off = new StudioHost(emitting: false);

        var outage = (await broken.SkillAnswer()).Gap;
        var never = (await off.SkillAnswer()).Gap;

        // Both answers are empty, and a caller that only counted events could not tell the two problems apart.
        Assert.Equal("unreachable", outage.Kind);
        Assert.Equal("telemetryOff", never.Kind);
        Assert.NotEqual(outage.Missing, never.Missing);
    }

    [Fact]
    public async Task Says_telemetry_is_off_even_where_the_store_has_events_from_before_it_was()
    {
        using var studio = new StudioHost(emitting: false);

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var answer = await studio.SkillAnswer();

        // The earlier Activations are real, but nothing has reached the events store since the switch went off.
        Assert.Equal("telemetryOff", answer.Gap.Kind);
        Assert.Contains("Telemetry switch", answer.Gap.Missing ?? "");
        Assert.NotEmpty(Assert.Single(answer.Day("2026-09-14").Skills).Origins);
    }

    [Fact]
    public async Task Says_it_cannot_tell_whether_telemetry_was_on_rather_than_saying_it_was_off()
    {
        using var studio = new StudioHost(settings: "{ not json");

        var answer = await studio.SkillAnswer();

        // Not "off": that would tell a developer to flip a switch Studio has refused to touch.
        Assert.Equal("telemetryUnknown", answer.Gap.Kind);
        Assert.Contains("cannot read", answer.Gap.Missing ?? "");
        Assert.Contains("Telemetry switch", answer.Gap.Missing ?? "");
    }

    [Fact]
    public async Task Says_nothing_is_missing_when_the_store_answered_with_events()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var answer = await studio.SkillAnswer();

        Assert.Equal("complete", answer.Gap.Kind);
        Assert.Null(answer.Gap.Missing);
    }

    [Fact]
    public async Task Says_nothing_is_missing_when_the_period_holds_turns_but_no_activations()
    {
        using var studio = new StudioHost();

        await studio.Push(new ApiRequest(GrilledAt, Skill: "grilling", CostUsd: 0.1m));

        var answer = await studio.SkillAnswer();

        // A skill that fired before the period can spend inside it, and a row of spend beside "quiet" contradicts itself.
        Assert.Equal(0.1m, Assert.Single(answer.Day("2026-09-14").Skills).Spend?.Cost);
        Assert.Equal("complete", answer.Gap.Kind);
        Assert.Null(answer.Gap.Missing);
    }

    [Fact]
    public async Task Ends_with_a_Gap_that_holds_only_its_kind_and_what_is_missing()
    {
        using var studio = new StudioHost();

        var end = await studio.SkillLine("end");

        // No start date: the head already names the days the answer covers.
        Assert.Equal(["gap", "kind"], StudioHost.Fields(end));
        Assert.Equal(["kind", "missing"], StudioHost.Fields(end["gap"]));
    }
}
