using System.Text.Json;
using System.Text.Json.Serialization;
using Skillworks.Core.Registration;
using Skillworks.ServiceDefaults;
using Skillworks.Studio.Api.Activations;
using Skillworks.Studio.Api.Catalogue;
using Skillworks.Studio.Api.Filters;
using Skillworks.Studio.Api.Health;
using Skillworks.Studio.Api.Ingest;
using Skillworks.Studio.Api.Skills;
using Skillworks.Studio.Api.Spend;
using Skillworks.Studio.Api.Telemetry;
using Skillworks.Studio.Api.Transcripts;

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

app.MapGroup("/api")
    .MapHealthEndpoints()
    .MapCatalogueEndpoints()
    .MapTranscriptEndpoints()
    .MapSkillEndpoints()
    .MapActivationEndpoints()
    .MapFilterEndpoints()
    .MapSpendEndpoints()
    .MapIngestEndpoints()
    .MapTelemetrySwitchEndpoints();

app.Run();

// The in-memory test host needs a handle on this assembly's entry point.
public partial class Program;
