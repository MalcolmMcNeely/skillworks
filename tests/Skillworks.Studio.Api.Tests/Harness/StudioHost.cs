using System.Text.Json;
using System.Text.Json.Nodes;
using Skillworks.Core.Telemetry;

namespace Skillworks.Studio.Api.Tests.Harness;

public sealed class StudioHost : IDisposable
{
    public static readonly JsonSerializerOptions Wire = new(JsonSerializerDefaults.Web);

    // Shares the switch's list, so this fixture cannot claim telemetry is on while Studio reads it as off.
    private static readonly string EmittingSettings = new JsonObject
    {
        ["env"] = new JsonObject(
            TelemetryVariables
                .For(new ClaudeSettingsOptions().CollectorEndpoint)
                .Select(variable => KeyValuePair.Create(variable.Key, (JsonNode?)JsonValue.Create(variable.Value)))),
    }.ToJsonString();

    private readonly TemporaryFolder _folder = new();
    private readonly PinnedClock _clock = new();

    // Its own tenant, so no other test's events reach this host's answers.
    private readonly string _tenant = Guid.NewGuid().ToString("N");

    private readonly StudioApiHost _api;
    private readonly HttpClient _client;

    public StudioHost(
        string? cataloguePath = null,
        // Only for a store that is down or failing; data comes from the test Loki.
        BrokenEventsStore? events = null,
        int maxEvents = 5000,
        // Not the developer's settings, or Gap tests would pass or fail on this machine's telemetry.
        bool emitting = true,
        string? settings = null,
        bool tenanted = true,
        int? lookbackDays = null)
    {
        var settingsPath = Path.Combine(_folder.Path, "settings.json");
        File.WriteAllText(settingsPath, settings ?? (emitting ? EmittingSettings : "{}"));

        // Left out unless asked for, as an empty value binds as zero days and would hide the default.
        (string Key, string? Value)[] lookback = lookbackDays is { } days ? [("Loki:LookbackDays", days.ToString())] : [];

        _api = new StudioApiHost(
            events,
            _clock,
            [
                ("Loki:Address", TestLoki.Address.ToString()),
                ("Loki:Tenant", tenanted ? _tenant : null),
                ("Loki:MaxEvents", maxEvents.ToString()),
                ("Loki:MaxQueryDays", TestLoki.MaxQueryDays.ToString()),
                ("ClaudeSettings:Path", settingsPath),
                ("ClaudeSettings:StampPath", Path.Combine(_folder.Path, "telemetry-switch.json")),
                ("Catalogue:Path", cataloguePath ?? Path.Combine(_folder.Path, "no-catalogue")),
                .. lookback,
            ]);

        _client = _api.CreateClient();
    }

    public HttpClient Client => _client;

    public Task Push(params SkillActivated[] events) => TestLoki.PushAsync(_tenant, events);

    public Task Push(params ApiRequest[] turns) => TestLoki.PushAsync(_tenant, turns);

    public static string Catalogue() => Path.Combine(AppContext.BaseDirectory, "Fixtures", "Catalogue");

    public static IReadOnlyList<string> Fields(JsonNode? answer) =>
        [.. (answer?.AsObject() ?? []).Select(field => field.Key).Order(StringComparer.Ordinal)];

    public void Dispose()
    {
        _client.Dispose();
        _api.Dispose();
        _folder.Dispose();
    }
}
