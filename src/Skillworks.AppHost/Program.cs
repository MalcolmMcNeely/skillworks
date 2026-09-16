using Skillworks.AppHost;

var builder = DistributedApplication.CreateBuilder(args);

// The catalogue is the folder beside us today; when it moves to its own repository, only this line changes.
var repositoryRoot = Path.GetFullPath(Path.Combine(builder.AppHostDirectory, "..", ".."));

// Persistent, pinned and unproxied: Claude Code sends events while the AppHost is stopped, to the address in its settings.
const int collectorPort = 4318;
var collectorAddress = "http://localhost:" + collectorPort;

var loki = builder.AddContainer("loki", LokiImage.Name, LokiImage.Tag)
    .WithLifetime(ContainerLifetime.Persistent)
    .WithVolume("skillworks-loki", "/loki")
    .WithHttpEndpoint(port: 3100, targetPort: 3100, name: "http", isProxied: false);

// The Collector reaches 4318 over the container network, so only the port Studio reads is pinned here.
var tempo = builder.AddContainer("tempo", TempoImage.Name, TempoImage.Tag)
    .WithLifetime(ContainerLifetime.Persistent)
    .WithVolume("skillworks-tempo", "/var/tempo")
    .WithBindMount(Path.Combine(builder.AppHostDirectory, "tempo.yaml"), "/etc/tempo/config.yaml", isReadOnly: true)
    .WithArgs("-config.file=/etc/tempo/config.yaml")
    .WithHttpEndpoint(port: 3200, targetPort: 3200, name: "http", isProxied: false);

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
    .WaitFor(loki)
    .WaitFor(tempo);

// No WaitFor on the containers: Studio starts without Loki, and its Gaps say the Events store is unreachable.
var api = builder.AddProject<Projects.Skillworks_Studio_Api>("api")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("Catalogue__Path", Path.Combine(repositoryRoot, "plugins"))
    .WithEnvironment("ClaudeSettings__CollectorEndpoint", collectorAddress)
    // Pinned, so the address holds whether or not Loki was up when Studio started.
    .WithEnvironment("Loki__Address", loki.GetEndpoint("http"))
    .WithEnvironment("Tempo__Address", tempo.GetEndpoint("http"));

// vite.config.ts proxies to the API_HTTP(S) address that WithReference injects, so no port is written down.
builder.AddViteApp("web", "../Skillworks.Studio.Web")
    .WithReference(api)
    .WaitFor(api);

builder.Build().Run();
