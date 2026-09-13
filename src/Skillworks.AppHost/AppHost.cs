var builder = DistributedApplication.CreateBuilder(args);

// ADR 0003: the catalogue path is configuration. Today it is the folder beside us; one day it is
// another repository, and only this line changes.
var repositoryRoot = Path.GetFullPath(Path.Combine(builder.AppHostDirectory, "..", ".."));

// ADR 0002: the events half of telemetry. Both containers are persistent and keep their data, so
// they go on catching events after the AppHost stops and while Studio is closed.
//
// Every host port here is pinned and unproxied. Aspire's proxy would hold the port and then die
// with the AppHost, and the collector's address is the one Studio writes into Claude Code's
// settings, where it has to still be right tomorrow.
const int collectorPort = 4318;
var collectorAddress = "http://localhost:" + collectorPort;

var loki = builder.AddContainer("loki", "grafana/loki", "3.5.9")
    .WithLifetime(ContainerLifetime.Persistent)
    .WithVolume("skillworks-loki", "/loki")
    .WithHttpEndpoint(port: 3100, targetPort: 3100, name: "http", isProxied: false);

builder.AddContainer("collector", "otel/opentelemetry-collector-contrib", "0.138.0")
    .WithLifetime(ContainerLifetime.Persistent)
    .WithVolume("skillworks-collector", "/var/lib/otelcol")
    .WithBindMount(
        Path.Combine(builder.AppHostDirectory, "otel-collector.yaml"),
        "/etc/otelcol-contrib/config.yaml",
        isReadOnly: true)
    // The image runs as a user that cannot write to a fresh volume, and the exporter queue has to.
    .WithContainerRuntimeArgs("--user", "0:0")
    .WithHttpEndpoint(port: collectorPort, targetPort: 4318, name: "otlp", isProxied: false)
    .WaitFor(loki);

// No WaitFor on the containers: ADR 0002 has Studio degrade rather than fail when they are down,
// because the transcript half is the durable record and stands on its own.
var api = builder.AddProject<Projects.Skillworks_Studio_Api>("api")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("Catalogue__Path", Path.Combine(repositoryRoot, "plugins"))
    .WithEnvironment("ClaudeSettings__CollectorEndpoint", collectorAddress);

// AddViteApp runs npm install and npm run dev itself, and injects the API address as API_HTTP(S),
// which vite.config.ts proxies to. Nothing hard codes a port.
builder.AddViteApp("web", "../Skillworks.Studio.Web")
    .WithReference(api)
    .WaitFor(api);

builder.Build().Run();
