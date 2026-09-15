using System.Net;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed partial class ActivationEndpointsTests
{
    [Fact]
    public async Task Says_the_list_is_cut_short_when_the_period_holds_more_firings_than_one_read_takes()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), maxEvents: 2);

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:10:00.000Z"));

        var answer = await studio.ActivationList();

        // The newest are kept, and the Gap says so, or a cut list would read as the whole week.
        Assert.Equal(
            [Moment("2026-09-14T09:10:00Z"), Moment("2026-09-14T09:05:00Z")],
            answer.Activations.Select(activation => activation.TimestampUtc));
        Assert.Equal("truncated", answer.Provenance.Gap);
        Assert.Contains("newest 2", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Says_the_events_store_could_not_be_read_rather_than_that_nothing_fired()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), events: events);

        var answer = await studio.ActivationList();

        Assert.Empty(answer.Activations);
        Assert.Equal("unreachable", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);
    }

    [Fact]
    public async Task Reports_an_events_store_that_answers_badly_as_unreachable_rather_than_as_quiet()
    {
        using var events = BrokenEventsStore.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), events: events);

        var answer = await studio.ActivationList();

        Assert.Equal("unreachable", answer.Provenance.Gap);
        Assert.Contains("502", answer.Provenance.Missing ?? "");
    }

    [Fact]
    public async Task Says_telemetry_was_never_switched_on_beside_an_empty_list()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), emitting: false);

        var answer = await studio.ActivationList();

        Assert.Empty(answer.Activations);
        Assert.Equal("telemetryOff", answer.Provenance.Gap);
    }

    [Fact]
    public async Task Says_it_cannot_tell_whether_telemetry_was_on_beside_an_empty_list()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), settings: "{ not json");

        var answer = await studio.ActivationList();

        Assert.Equal("telemetryUnknown", answer.Provenance.Gap);
    }

    [Fact]
    public async Task Labels_a_period_the_events_store_holds_nothing_for_as_quiet()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        var answer = await studio.ActivationList();

        Assert.Empty(answer.Activations);
        Assert.Equal("quiet", answer.Provenance.Gap);
        Assert.NotNull(answer.Provenance.Missing);
    }

    [Fact]
    public async Task Says_nothing_is_missing_when_only_the_filter_matched_nothing()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        await studio.Push(new SkillActivated("grilling", GrilledAt));

        var answer = await studio.ActivationList("?skill=tdd");

        // Other skills fired this week, so "quiet" would send a reader looking for a telemetry fault.
        Assert.Empty(answer.Activations);
        Assert.Equal("complete", answer.Provenance.Gap);
        Assert.Null(answer.Provenance.Missing);
    }
}
