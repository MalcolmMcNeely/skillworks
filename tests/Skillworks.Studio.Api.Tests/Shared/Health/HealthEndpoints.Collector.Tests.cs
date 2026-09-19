using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Shared.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Shared.Health;

public sealed partial class HealthEndpointsTests
{
    [Fact]
    public async Task Says_the_collector_answered_when_both_of_its_doors_did()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        var part = await studio.Part("Collector");

        Assert.Equal("working", part.State);
        Assert.Contains("answered", part.Detail);
    }

    [Fact]
    public async Task Reports_a_collector_that_refuses_spans_as_broken_and_names_the_shut_door()
    {
        using var collector = FakeCollector.SpansShut();
        using var studio = new StudioHost(StudioHost.Catalogue(), collector: collector);

        var part = await studio.Part("Collector");

        Assert.Equal("broken", part.State);
        Assert.Contains("Spans door", part.Detail);
        Assert.Contains("404", part.Detail);
    }

    [Fact]
    public async Task Reports_a_collector_that_refuses_events_as_broken_and_names_the_shut_door()
    {
        using var collector = FakeCollector.EventsShut();
        using var studio = new StudioHost(StudioHost.Catalogue(), collector: collector);

        var part = await studio.Part("Collector");

        Assert.Equal("broken", part.State);
        Assert.Contains("events door", part.Detail);
        Assert.Contains("404", part.Detail);
    }

    [Fact]
    public async Task Reports_a_collector_nothing_answers_for_as_broken()
    {
        using var collector = FakeCollector.Down();
        using var studio = new StudioHost(StudioHost.Catalogue(), collector: collector);

        var part = await studio.Part("Collector");

        Assert.Equal("broken", part.State);
        Assert.Contains("could not be reached", part.Detail);
    }

    [Fact]
    public async Task Tells_the_developer_to_restart_the_collector_so_that_it_reads_its_settings_again()
    {
        using var collector = FakeCollector.SpansShut();
        using var studio = new StudioHost(StudioHost.Catalogue(), collector: collector);

        var part = await studio.Part("Collector");

        Assert.Contains("Restart the Collector", part.Action ?? "");
        Assert.Contains("settings", part.Action ?? "");
    }

    [Fact]
    public async Task Reports_one_shut_door_against_the_collector_alone()
    {
        using var collector = FakeCollector.SpansShut();
        using var studio = new StudioHost(StudioHost.Catalogue(), collector: collector);

        var broken = (await studio.Health()).Parts.Where(part => part.State == "broken").Select(part => part.Name);

        // A part is one Lamp, or a developer is sent after a store that is working.
        Assert.Equal(["Collector"], broken);
    }

    [Fact]
    public async Task Never_reads_the_collector_as_off_whether_it_is_answering_or_not()
    {
        using var down = FakeCollector.Down();
        using var stopped = new StudioHost(StudioHost.Catalogue(), collector: down, emitting: false, tracing: false);
        using var running = new StudioHost(StudioHost.Catalogue(), emitting: false, tracing: false);

        Assert.Equal("broken", (await stopped.Part("Collector")).State);
        Assert.Equal("working", (await running.Part("Collector")).State);
    }

    [Fact]
    public async Task Tells_a_shut_spans_door_apart_from_a_trace_store_that_stopped_answering()
    {
        using var collector = FakeCollector.SpansShut();
        using var shut = new StudioHost(StudioHost.Catalogue(), collector: collector);
        using var traces = BrokenTraceStore.Down();
        using var down = new StudioHost(StudioHost.Catalogue(), traces: traces);

        // A Session reads Thin either way, but the part at fault and the developer's next step differ.
        Assert.Equal("broken", (await shut.Part("Collector")).State);
        Assert.Equal("working", (await shut.Part("Trace store")).State);

        Assert.Equal("working", (await down.Part("Collector")).State);
        Assert.Equal("broken", (await down.Part("Trace store")).State);
    }

    [Fact]
    public async Task Knocks_on_the_same_address_it_writes_into_the_developer_settings()
    {
        using var studio = new StudioHost(StudioHost.Catalogue(), collectorAddress: "   ");

        // A Lamp that settled a blank address differently would pass a door Claude Code never sends to.
        Assert.Equal("working", (await studio.Part("Claude Code telemetry")).State);
        Assert.Contains("localhost:4318", (await studio.Part("Collector")).Detail);
    }

    [Fact]
    public async Task Knocks_on_each_door_with_a_payload_that_holds_no_event_and_no_span()
    {
        using var collector = FakeCollector.Open();
        using var studio = new StudioHost(StudioHost.Catalogue(), collector: collector);

        await studio.Health();

        // Reading Health must move no figure a reader is about to read.
        Assert.Equal("""{"resourceLogs":[]}""", collector.EventsPayload);
        Assert.Equal("""{"resourceSpans":[]}""", collector.SpansPayload);
    }
}
