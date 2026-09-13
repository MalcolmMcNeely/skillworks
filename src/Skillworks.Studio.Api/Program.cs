using Skillworks.Core;
using Skillworks.Core.Catalogue;
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

app.Run();

// The in-memory test host needs a handle on this assembly's entry point.
public partial class Program;
