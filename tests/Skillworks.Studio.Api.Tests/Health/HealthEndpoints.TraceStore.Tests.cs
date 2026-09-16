using System.Net;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Health;

public sealed partial class HealthEndpointsTests
{
    [Fact]
    public async Task Says_the_trace_store_answered_when_it_did()
    {
        using var studio = new StudioHost(StudioHost.Catalogue());

        var part = await studio.Part("Trace store");

        Assert.Equal("working", part.State);
        Assert.Contains("answered", part.Detail);
    }

    [Fact]
    public async Task Reports_a_trace_store_that_is_down_as_broken_and_says_how_to_start_it()
    {
        using var traces = BrokenTraceStore.Down();
        using var studio = new StudioHost(StudioHost.Catalogue(), traces: traces);

        var part = await studio.Part("Trace store");

        Assert.Equal("broken", part.State);
        Assert.Contains("aspire run", part.Action ?? "");
    }

    [Fact]
    public async Task Reports_a_trace_store_that_answers_badly_as_broken_too()
    {
        using var traces = BrokenTraceStore.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(StudioHost.Catalogue(), traces: traces);

        var part = await studio.Part("Trace store");

        Assert.Equal("broken", part.State);
        Assert.Contains("502", part.Detail);
    }

    [Fact]
    public async Task Reports_a_trace_store_that_is_still_starting_as_starting_rather_than_as_broken()
    {
        using var traces = BrokenTraceStore.StartingUp();
        using var studio = new StudioHost(StudioHost.Catalogue(), traces: traces);

        var part = await studio.Part("Trace store");

        // A container part way through coming up fixes itself, so a developer sent to restart it would wait longer.
        Assert.Equal("starting", part.State);
        Assert.Contains("moment", part.Action ?? "");
    }

    [Fact]
    public async Task Reports_a_multi_tenant_trace_store_as_broken_when_studio_names_no_tenant()
    {
        using var studio = new StudioHost(StudioHost.Catalogue(), tenanted: false);

        var part = await studio.Part("Trace store");

        // The test Tempo refuses a read that names no tenant, so this is Studio sending none.
        Assert.Equal("broken", part.State);
        Assert.Contains("401", part.Detail);
    }

    [Fact]
    public async Task Reports_traces_that_were_never_switched_on_as_off_rather_than_as_broken()
    {
        using var studio = new StudioHost(StudioHost.Catalogue(), tracing: false);

        var part = await studio.Part("Trace store");

        // Not a fault: reporting one would send a developer after a container problem that does not exist.
        Assert.Equal("off", part.State);

        // The action has to be one that works today, and the switch does not write these two yet.
        Assert.Contains("OTEL_TRACES_EXPORTER", part.Action ?? "");
        Assert.Contains("CLAUDE_CODE_ENHANCED_TELEMETRY_BETA", part.Action ?? "");
    }

    [Fact]
    public async Task Tells_a_trace_store_that_is_down_apart_from_traces_that_are_switched_off()
    {
        using var down = BrokenTraceStore.Down();
        using var broken = new StudioHost(StudioHost.Catalogue(), traces: down);
        using var off = new StudioHost(StudioHost.Catalogue(), tracing: false);

        // A Session reads Thin either way, but the part at fault and the developer's next step differ.
        Assert.Equal("broken", (await broken.Part("Trace store")).State);
        Assert.Equal("off", (await off.Part("Trace store")).State);
    }

    [Fact]
    public async Task Tells_the_two_stores_apart_when_only_one_of_them_is_down()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(StudioHost.Catalogue(), events: events);

        var health = await studio.Health();

        // Each store answers on its own, so an outage in one says nothing about the other.
        Assert.Equal("broken", health.Parts.Single(part => part.Name == "Events store").State);
        Assert.Equal("working", health.Parts.Single(part => part.Name == "Trace store").State);
    }
}
