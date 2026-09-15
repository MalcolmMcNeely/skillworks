using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
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

    private readonly TemporaryFolder _data = new();
    private readonly PinnedClock _clock = new();

    // Its own tenant, so no other test's events reach this host's answers.
    private readonly string _tenant = Guid.NewGuid().ToString("N");

    private readonly StudioApiHost _api;
    private readonly HttpClient _client;

    public StudioHost(
        string? transcriptPath,
        string? cataloguePath = null,
        // Zero, so no pass runs that a test did not ask for and the pass counts tests wait on stay exact.
        int sweepSeconds = 0,
        // Only for a store that is down or failing; data comes from the test Loki.
        BrokenEventsStore? events = null,
        int maxEvents = 5000,
        // Not the developer's settings, or provenance tests would pass or fail on this machine's telemetry.
        bool emitting = true,
        string? settings = null,
        bool tenanted = true,
        int? lookbackDays = null)
    {
        var settingsPath = Path.Combine(_data.Path, "settings.json");
        File.WriteAllText(settingsPath, settings ?? (emitting ? EmittingSettings : "{}"));

        // Left out unless asked for, as an empty value binds as zero days and would hide the default.
        (string Key, string? Value)[] lookback = lookbackDays is { } days ? [("Loki:LookbackDays", days.ToString())] : [];

        _api = new StudioApiHost(
            events,
            _clock,
            [
                ("Transcripts:Path", transcriptPath),
                ("TranscriptStore:DatabasePath", Path.Combine(_data.Path, "transcript-store.db")),
                ("TranscriptStore:SweepSeconds", sweepSeconds.ToString()),
                ("Loki:Address", TestLoki.Address.ToString()),
                ("Loki:Tenant", tenanted ? _tenant : null),
                ("Loki:MaxEvents", maxEvents.ToString()),
                ("Loki:MaxQueryDays", TestLoki.MaxQueryDays.ToString()),
                ("ClaudeSettings:Path", settingsPath),
                ("ClaudeSettings:StampPath", Path.Combine(_data.Path, "telemetry-switch.json")),
                ("Catalogue:Path", cataloguePath ?? Path.Combine(_data.Path, "no-catalogue")),
                .. lookback,
            ]);

        _client = _api.CreateClient();
    }

    public HttpClient Client => _client;

    public DateTimeOffset Now => _clock.GetUtcNow();

    public Task Push(params SkillActivated[] events) => TestLoki.PushAsync(_tenant, events);

    public Task Push(params ApiRequest[] turns) => TestLoki.PushAsync(_tenant, turns);

    public static string Fixture(string name) => Path.Combine(AppContext.BaseDirectory, "Fixtures", "Transcripts", name);

    public static string Catalogue() => Path.Combine(AppContext.BaseDirectory, "Fixtures", "Catalogue");

    public async Task WaitForIngestPasses(int passes)
    {
        var deadline = DateTime.UtcNow.AddSeconds(30);

        while ((await Status()).CompletedPasses < passes)
        {
            if (DateTime.UtcNow > deadline)
            {
                throw new TimeoutException($"Ingest never reached pass {passes}.");
            }

            await Task.Delay(20);
        }
    }

    public async Task<IngestRow> Status()
    {
        return await _client.GetFromJsonAsync<IngestRow>("/api/ingest", Wire)
            ?? throw new InvalidOperationException("The ingest status came back empty.");
    }

    public Task IngestAgain() => AskAndWait("/api/ingest");

    public Task FullIngest() => AskAndWait("/api/ingest/full");

    public void Dispose()
    {
        _client.Dispose();
        _api.Dispose();

        // SQLite pools its connections, so the file stays open past the host and the directory will not delete.
        SqliteConnection.ClearAllPools();
        _data.Dispose();
    }

    private async Task AskAndWait(string route)
    {
        await WaitForIngestPasses(1);
        var passes = (await Status()).CompletedPasses;

        using var response = await _client.PostAsync(route, content: null);
        response.EnsureSuccessStatusCode();

        await WaitForIngestPasses(passes + 1);
    }
}
