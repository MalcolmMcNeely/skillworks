using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace Skillworks.Studio.Api.Tests;

/// <summary>
/// One running Studio pointed at a throwaway Claude Code settings file, so a test can watch the
/// telemetry switch read and write a real document without going near the developer's own.
/// </summary>
public sealed class TelemetryStudio : IDisposable
{
    /// <summary>Stands in for the collector's pinned address, which the AppHost publishes.</summary>
    public const string Collector = "http://localhost:4318";

    private static readonly JsonSerializerOptions Wire = new(JsonSerializerDefaults.Web);

    private readonly TemporaryFolder _folder = new();
    private readonly StudioApi _api;
    private readonly HttpClient _client;
    private readonly string _settingsPath;

    /// <param name="settings">The settings file's exact text. Null leaves no file there at all.</param>
    public TelemetryStudio(string? settings = null)
    {
        _settingsPath = Path.Combine(_folder.Path, "settings.json");

        if (settings is not null)
        {
            File.WriteAllText(_settingsPath, settings);
        }

        _api = new StudioApi(
            Events.Holding(),
            ("ClaudeSettings:Path", _settingsPath),
            ("ClaudeSettings:StampPath", Path.Combine(_folder.Path, "telemetry-switch.json")),
            ("ClaudeSettings:CollectorEndpoint", Collector),
            ("Transcripts:Path", _folder.Subfolder("no-transcripts")),
            ("Telemetry:DatabasePath", Path.Combine(_folder.Path, "telemetry.db")),
            ("Telemetry:SweepSeconds", "0"),
            ("Catalogue:Path", Path.Combine(_folder.Path, "no-catalogue")));

        _client = _api.CreateClient();
    }

    public Task<JsonElement> State() => _client.GetFromJsonAsync<JsonElement>("/api/telemetry/switch");

    /// <summary>Flips the switch and hands back the raw response, so a test can assert a refusal.</summary>
    public Task<HttpResponseMessage> Flip(bool emitting) =>
        _client.PutAsJsonAsync("/api/telemetry/switch", new { emitting }, Wire);

    /// <summary>Flips the switch and fails the test if Studio refused to write.</summary>
    public async Task<JsonElement> Turn(bool emitting)
    {
        using var response = await Flip(emitting);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public bool SettingsExist() => File.Exists(_settingsPath);

    public string SettingsText() => File.ReadAllText(_settingsPath);

    /// <summary>Puts new text in the file behind Studio's back, as a developer with an editor would.</summary>
    public void RewriteSettings(string settings) => File.WriteAllText(_settingsPath, settings);

    public JsonElement Settings() => JsonDocument.Parse(SettingsText()).RootElement.Clone();

    /// <summary>One environment variable as it stands on disk, or null when it is not there.</summary>
    public string? Variable(string name)
    {
        var settings = Settings();

        return settings.TryGetProperty("env", out var environment)
            && environment.TryGetProperty(name, out var value)
                ? value.GetString()
                : null;
    }

    /// <summary>Every variable the state says turning telemetry on would write, and its new value.</summary>
    public static Dictionary<string, string> Changes(JsonElement state) =>
        state.GetProperty("changes")
            .EnumerateArray()
            .ToDictionary(
                change => change.GetProperty("name").GetString()!,
                change => change.GetProperty("to").GetString()!);

    public void Dispose()
    {
        _client.Dispose();
        _api.Dispose();

        // SQLite pools its connections, so the file stays open past the host and the directory
        // will not delete.
        SqliteConnection.ClearAllPools();
        _folder.Dispose();
    }
}
