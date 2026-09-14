using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed partial class ActivationEndpointsTests
{
    private const string GrilledAt = "2026-09-02T14:48:23.182Z";

    [Fact]
    public async Task Says_whether_claude_chose_a_skill_or_a_developer_typed_it()
    {
        using var events = Events.Holding(
            new Event("grilling", "2026-09-02T14:48:23.100Z", Trigger: "user-slash", Source: "userSettings"));
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), events: events);

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
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), events: events);

        var listed = Assert.Single(await studio.Activations());

        Assert.Equal("claude-proactive", listed.Origin?.Trigger);
    }

    [Fact]
    public async Task Says_telemetry_is_off_beside_one_firing_as_well_as_beside_the_table()
    {
        using var events = Events.Holding();
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), events: events, emitting: false);

        var opened = await studio.OpenActivation(Grilling);

        // The same question asked of one firing. A detail page that stayed silent would leave the
        // empty trigger beside it to be read as "Claude did not choose this one".
        Assert.Equal("telemetryOff", opened.Provenance.Gap);
        Assert.Null(opened.Activation.Origin);
    }

    [Fact]
    public async Task Leaves_a_firing_with_no_event_near_it_without_an_origin()
    {
        using var events = Events.Holding(new Event("grilling", "2026-09-02T11:00:00.000Z", Trigger: "user-slash"));
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), events: events);

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
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), events: events);

        var opened = await studio.Activation(Grilling);

        Assert.Equal("claude-proactive", opened.Origin?.Trigger);
    }
}
