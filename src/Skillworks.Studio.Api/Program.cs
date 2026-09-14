using System.Text.Json;
using System.Text.Json.Serialization;
using Skillworks.Core;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Health;
using Skillworks.Core.Settings;
using Skillworks.Core.Skills;
using Skillworks.Core.Telemetry;
using Skillworks.Core.Transcripts;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.Services.AddSkillworksCore(builder.Configuration);

// Enums by name, cased like every other name on the wire. A number would make "the events store is
// down" and "telemetry was never switched on" a 1 and a 2, which is a thing to look up rather than
// a thing to read.
builder.Services.ConfigureHttpJsonOptions(json =>
    json.SerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.CamelCase)));

var app = builder.Build();

app.MapDefaultEndpoints();

var api = app.MapGroup("/api");

// One place that says which parts of Studio are doing their job, so an empty screen elsewhere is
// explained rather than mysterious. It probes the events store, so it is a read of the outside
// world rather than a cached opinion about it.
api.MapGet("health", (StudioHealth health, CancellationToken cancellationToken) =>
    health.ReportAsync(cancellationToken));

api.MapGet("catalogue", (CatalogueLocator locator) => locator.Locate());

api.MapGet("transcripts", (TranscriptLocator locator) => locator.Locate());

// Every list of telemetry takes the same filter set, bound as one object rather than four
// parameters, so the next list to arrive narrows the same way without being asked to remember how.
// The prices and the ingest faults below take none of it: a price is configuration, and a fault
// names a file rather than a skill, a repository or a moment a skill fired.
api.MapGet("skills", ([AsParameters] TelemetryFilter filter, SkillReport report, CancellationToken cancellationToken) =>
    report.SkillsAsync(filter, cancellationToken));

api.MapGet("activations", ([AsParameters] TelemetryFilter filter, ActivationReport activations, CancellationToken cancellationToken) =>
    activations.ListAsync(filter, cancellationToken));

// No filter here. A reader who has a firing's id is asking about that firing, and narrowing it
// would answer a link with a blank page whenever the filter had moved on.
api.MapGet("activations/{id}", async (string id, ActivationReport activations, CancellationToken cancellationToken) =>
    await activations.OpenAsync(id, cancellationToken) is { } activation
        ? Results.Ok(activation)
        : Results.NotFound());

api.MapGet("filters", (SkillReport report, CancellationToken cancellationToken) =>
    report.ChoicesAsync(cancellationToken));

// Prices are configuration, not data: they are read on every skill query and changing one changes
// what the next answer says without a transcript being read again.
api.MapGet("prices", (PriceTable prices, CancellationToken cancellationToken) =>
    prices.PricesAsync(cancellationToken));

api.MapPut("prices", async (ModelPrice price, PriceTable prices, CancellationToken cancellationToken) =>
    Results.Ok(await prices.SetAsync(price, cancellationToken)));

api.MapGet("ingest", (IngestReport report, CancellationToken cancellationToken) =>
    report.StatusAsync(cancellationToken));

api.MapPost("ingest", async (IngestReport report, CancellationToken cancellationToken) =>
    Results.Accepted(value: await report.RequestPassAsync(full: false, cancellationToken)));

// A route of its own, not a flag on the one above: a full re-ingest throws away everything already
// read, and that should not be reachable by mistyping a query string.
api.MapPost("ingest/full", async (IngestReport report, CancellationToken cancellationToken) =>
    Results.Accepted(value: await report.RequestPassAsync(full: true, cancellationToken)));

api.MapGet("ingest/faults", (IngestReport report, CancellationToken cancellationToken) =>
    report.FaultsAsync(cancellationToken));

// The GET carries the preview, so the front end can show the exact change and ask before the PUT.
api.MapGet("telemetry/switch", (TelemetrySwitch telemetry) => telemetry.State());

api.MapPut("telemetry/switch", (TelemetrySwitchRequest request, TelemetrySwitch telemetry) =>
{
    var result = request.Emitting ? telemetry.TurnOn() : telemetry.TurnOff();

    // A refusal is a conflict with the document on disk, not a bad request: the settings have to
    // change before the same call can succeed.
    return result.Refusal is null
        ? Results.Ok(result.State)
        : Results.Problem(result.Refusal, statusCode: StatusCodes.Status409Conflict);
});

app.Run();

public sealed record TelemetrySwitchRequest(bool Emitting);

// The in-memory test host needs a handle on this assembly's entry point.
public partial class Program;
