using System.Text.Json;
using System.Text.Json.Serialization;
using Skillworks.Core.Sessions;
using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Catalogue;
using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Shared.Gaps;
using Skillworks.Core.Shared.Health;
using Skillworks.Core.Shared.Stores;
using Skillworks.Core.Shared.Telemetry;
using Skillworks.Core.Watch;
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

builder.Services
    .AddArriving()
    .AddCatalogue(builder.Configuration)
    .AddFilters()
    .AddGaps()
    .AddHealth()
    .AddStores(builder.Configuration)
    .AddTelemetry(builder.Configuration)
    .AddSessions()
    .AddWatch();

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
