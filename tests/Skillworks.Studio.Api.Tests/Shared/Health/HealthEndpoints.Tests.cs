using System.Net;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Shared.Health;

public sealed partial class HealthEndpointsTests
{
    [Fact]
    public async Task Reports_every_part_of_studio_in_one_answer()
    {
        using var studio = new StudioHost(StudioHost.Marketplace());

        // Sorted here, because the report's order is the screen's choice and not part of the answer.
        var parts = (await studio.Health()).Parts.Select(part => part.Name).Order();

        // A part missing from here is a part a developer has to go and check by hand.
        Assert.Equal(["Claude Code telemetry", "Collector", "Events store", "Marketplace", "Trace store"], parts);
    }

    [Fact]
    public async Task Answers_with_its_parts_alone()
    {
        using var studio = new StudioHost(StudioHost.Marketplace());

        // An empty screen is explained by its Gap, so health carries no reason for one.
        Assert.Equal(["parts"], await studio.HealthFields());
    }

    [Fact]
    public async Task Says_every_part_is_working_and_leaves_nothing_to_do_when_nothing_is_wrong()
    {
        using var studio = new StudioHost(StudioHost.Marketplace());

        var health = await studio.Health();

        Assert.All(health.Parts, part => Assert.Equal("working", part.State));
        Assert.All(health.Parts, part => Assert.Null(part.Action));
    }

    [Fact]
    public async Task Says_the_events_store_answered_when_it_did()
    {
        using var studio = new StudioHost(StudioHost.Marketplace());

        var part = await studio.Part("Events store");

        Assert.Equal("working", part.State);
        Assert.Contains("answered", part.Detail);
    }

    [Fact]
    public async Task Points_no_part_at_transcripts_or_the_ingest_when_every_part_needs_attention()
    {
        using var events = BrokenEventsStore.Down();
        using var collector = FakeCollector.Down();
        using var studio = new StudioHost(events: events, collector: collector, emitting: false, tracing: false);

        var health = await studio.Health();

        Assert.All(health.Parts, part => Assert.NotEqual("working", part.State));

        // Studio reads neither, so a developer sent after one would chase something that is not there.
        Assert.All(health.Parts, part =>
        {
            var said = $"{part.Detail} {part.Action}";

            Assert.DoesNotContain("transcript", said, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("ingest", said, StringComparison.OrdinalIgnoreCase);
        });
    }

    [Fact]
    public async Task Says_it_cannot_tell_whether_telemetry_is_on_when_it_cannot_read_the_settings()
    {
        using var studio = new StudioHost(StudioHost.Marketplace(), settings: "{ not json");

        var part = await studio.Part("Claude Code telemetry");

        // Broken, not off: a panel that guessed "off" would send a developer to write a file Studio has refused.
        Assert.Equal("broken", part.State);
        Assert.Contains("cannot read", part.Detail);
    }

    [Fact]
    public async Task Reports_an_events_store_that_is_down_as_broken_and_says_how_to_start_it()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(StudioHost.Marketplace(), events: events);

        var part = await studio.Part("Events store");

        Assert.Equal("broken", part.State);
        Assert.Contains("aspire run", part.Action ?? "");
    }

    [Fact]
    public async Task Reports_an_events_store_that_answers_badly_as_broken_too()
    {
        using var events = BrokenEventsStore.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(StudioHost.Marketplace(), events: events);

        var part = await studio.Part("Events store");

        // Asked directly, so an events store that is up and unhappy never reads as one with nothing in it.
        Assert.Equal("broken", part.State);
        Assert.Contains("502", part.Detail);
    }

    [Fact]
    public async Task Reads_the_events_store_with_a_real_query_rather_than_asking_if_it_is_up()
    {
        using var events = BrokenEventsStore.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(StudioHost.Marketplace(), events: events);

        await studio.Part("Events store");

        // Asking only whether it is up would pass a store that refuses LogQL, and every Measure would read a dash.
        Assert.Contains("query_range", events.Asked.Single());
        Assert.Contains("service_name", events.Asked.Single());
    }

    [Fact]
    public async Task Reports_telemetry_that_was_never_switched_on_as_off_rather_than_as_broken()
    {
        using var studio = new StudioHost(StudioHost.Marketplace(), emitting: false);

        var part = await studio.Part("Claude Code telemetry");

        // Not a fault: reporting one would send a developer after a container problem that does not exist.
        Assert.Equal("off", part.State);
        Assert.Contains("Telemetry switch", part.Action ?? "");
    }

    [Fact]
    public async Task Tells_a_store_that_is_down_apart_from_telemetry_that_is_switched_off()
    {
        using var down = BrokenEventsStore.Down();
        using var broken = new StudioHost(StudioHost.Marketplace(), events: down);
        using var off = new StudioHost(StudioHost.Marketplace(), emitting: false);

        var outage = await broken.Health();
        var never = await off.Health();

        // The same screen goes empty either way, but the part at fault and the developer's next step differ.
        Assert.Equal("broken", outage.Parts.Single(part => part.Name == "Events store").State);
        Assert.Equal("working", outage.Parts.Single(part => part.Name == "Claude Code telemetry").State);

        Assert.Equal("working", never.Parts.Single(part => part.Name == "Events store").State);
        Assert.Equal("off", never.Parts.Single(part => part.Name == "Claude Code telemetry").State);
    }

    [Fact]
    public async Task Names_the_missing_Marketplace_and_what_it_costs()
    {
        using var studio = new StudioHost();

        var part = await studio.Part("Marketplace");

        Assert.Equal("broken", part.State);
        Assert.Contains("Marketplace:Path", part.Action ?? "");
    }
}
