using Skillworks.Core;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Settings;
using Skillworks.Core.Skills;
using Skillworks.Core.Telemetry;
using Skillworks.Core.Transcripts;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.Services.AddSkillworksCore(builder.Configuration);

var app = builder.Build();

app.MapDefaultEndpoints();

var api = app.MapGroup("/api");

api.MapGet("catalogue", (CatalogueLocator locator) => locator.Locate());

api.MapGet("transcripts", (TranscriptLocator locator) => locator.Locate());

api.MapGet("skills", (SkillReport report, CancellationToken cancellationToken) =>
    report.SkillsAsync(cancellationToken));

api.MapGet("ingest", (IngestState state) => state.Status());

api.MapPost("ingest", (IngestState state) =>
{
    state.RequestPass();
    return Results.Accepted(value: state.Status());
});

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

/// <param name="Emitting">True asks Studio to turn telemetry on, false to turn it off again.</param>
public sealed record TelemetrySwitchRequest(bool Emitting);

// The in-memory test host needs a handle on this assembly's entry point.
public partial class Program;
