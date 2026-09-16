using System.Text.Json;
using System.Text.Json.Nodes;
using Skillworks.Core.Telemetry;
// Owned by the test project of the reader it serves, and linked into this one.
using Skillworks.Core.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Harness;

public sealed class StudioHost : IDisposable
{
    public static readonly JsonSerializerOptions Wire = new(JsonSerializerDefaults.Web);

    // Shares the switch's lists, so this fixture cannot claim telemetry is on while Studio reads it as off.
    private static string Settings(bool emitting, bool tracing) => new JsonObject
    {
        ["env"] = new JsonObject(
            Owned(emitting, tracing)
                .Select(variable => KeyValuePair.Create(variable.Key, (JsonNode?)JsonValue.Create(variable.Value)))),
    }.ToJsonString();

    private static IEnumerable<KeyValuePair<string, string>> Owned(bool emitting, bool tracing) =>
    [
        .. emitting ? TelemetryVariables.For(new ClaudeSettingsOptions().CollectorEndpoint) : [],
        .. tracing ? TelemetryVariables.Traces : [],
    ];

    private readonly TemporaryFolder _folder = new();
    private readonly PinnedClock _clock = new();

    // Its own tenant, so no other test's events reach this host's answers.
    private readonly string _tenant = Guid.NewGuid().ToString("N");

    private readonly StudioApiHost _api;
    private readonly HttpClient _client;

    public StudioHost(
        string? cataloguePath = null,
        // Only for a store that is down, failing or stops part way; data comes from the test Loki.
        BrokenEventsStore? events = null,
        // Only for a store that is down, failing or still starting; spans come from the test Tempo.
        BrokenTraceStore? traces = null,
        // Not the developer's settings, or Gap tests would pass or fail on this machine's telemetry.
        bool emitting = true,
        bool tracing = true,
        string? settings = null,
        bool tenanted = true,
        int? lookbackDays = null)
    {
        var settingsPath = Path.Combine(_folder.Path, "settings.json");
        File.WriteAllText(settingsPath, settings ?? Settings(emitting, tracing));

        // Left out unless asked for, as an empty value binds as zero days and would hide the default.
        (string Key, string? Value)[] lookback = lookbackDays is { } days ? [("Loki:LookbackDays", days.ToString())] : [];

        _api = new StudioApiHost(
            events,
            traces,
            _clock,
            [
                ("Loki:Address", TestLoki.Address.ToString()),
                ("Loki:Tenant", tenanted ? _tenant : null),
                ("Loki:MaxQueryDays", TestLoki.MaxQueryDays.ToString()),
                ("Tempo:Address", TestTempo.Address.ToString()),
                ("Tempo:Tenant", tenanted ? _tenant : null),
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

    public Task Push(params SessionEvent[] events) => TestLoki.PushAsync(_tenant, events);

    // Headers first and then one line at a time, as a browser reads an answer that arrives day by day.
    public async Task<IReadOnlyList<JsonObject>> Lines(string path, int count = int.MaxValue)
    {
        using var response = await _client.GetAsync(path, HttpCompletionOption.ResponseHeadersRead);

        response.EnsureSuccessStatusCode();

        using var body = new StreamReader(await response.Content.ReadAsStreamAsync());
        var lines = new List<JsonObject>();

        while (lines.Count < count && await body.ReadLineAsync() is { } line)
        {
            lines.Add(JsonNode.Parse(line)?.AsObject() ?? throw new InvalidOperationException("A line held null."));
        }

        return lines;
    }

    public static string? KindOf(JsonObject line) => (string?)line["kind"];

    public static T Read<T>(JsonNode? line) =>
        line.Deserialize<T>(Wire) ?? throw new InvalidOperationException($"A {typeof(T).Name} came back empty.");

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
