using System.Text.Json;
using System.Text.Json.Serialization;
using Skillworks.Core.Registration;
using Skillworks.ServiceDefaults;
using Skillworks.Studio.Api.Watch.Activations;
using Skillworks.Studio.Api.Shared.Catalogue;
using Skillworks.Studio.Api.Shared.Filters;
using Skillworks.Studio.Api.Shared.Health;
using Skillworks.Studio.Api.Sessions;
using Skillworks.Studio.Api.Watch.Skills;
using Skillworks.Studio.Api.Shared.Telemetry;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.Services.AddSkillworksCore(builder.Configuration);

// Enums by name, so "events store down" and "telemetry never switched on" read as words, not a 1 and a 2.
builder.Services.ConfigureHttpJsonOptions(json =>
    json.SerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.CamelCase)));

var app = builder.Build();

app.MapDefaultEndpoints();

app.MapGroup("/api")
    .MapHealthEndpoints()
    .MapCatalogueEndpoints()
    .MapSkillEndpoints()
    .MapActivationEndpoints()
    .MapSessionEndpoints()
    .MapFilterEndpoints()
    .MapTelemetrySwitchEndpoints();

app.Run();

// The in-memory test host needs a handle on this assembly's entry point.
public partial class Program;
