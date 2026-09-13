using Skillworks.Core;
using Skillworks.Core.Catalogue;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();
builder.Services.AddSkillworksCore(builder.Configuration);

var app = builder.Build();

app.MapDefaultEndpoints();

var api = app.MapGroup("/api");

api.MapGet("catalogue", (CatalogueLocator locator) => locator.Locate());

app.Run();

// The in-memory test host needs a handle on this assembly's entry point.
public partial class Program;
