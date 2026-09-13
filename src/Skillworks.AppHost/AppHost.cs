var builder = DistributedApplication.CreateBuilder(args);

// ADR 0003: the catalogue path is configuration. Today it is the folder beside us; one day it is
// another repository, and only this line changes.
var repositoryRoot = Path.GetFullPath(Path.Combine(builder.AppHostDirectory, "..", ".."));

var api = builder.AddProject<Projects.Skillworks_Studio_Api>("api")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("Catalogue__Path", Path.Combine(repositoryRoot, "plugins"));

// AddViteApp runs npm install and npm run dev itself, and injects the API address as API_HTTP(S),
// which vite.config.ts proxies to. Nothing hard codes a port.
builder.AddViteApp("web", "../Skillworks.Studio.Web")
    .WithReference(api)
    .WaitFor(api);

builder.Build().Run();
