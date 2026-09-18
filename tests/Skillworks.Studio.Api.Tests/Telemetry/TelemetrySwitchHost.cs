using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Telemetry;

public sealed class TelemetrySwitchHost : IDisposable
{
    public const string Collector = "http://localhost:4318";

    public const string StampName = "telemetry-switch.json";

    public static readonly JsonSerializerOptions Wire = new(JsonSerializerDefaults.Web);

    private readonly TemporaryFolder _folder = new();
    private readonly StudioApiHost _api;
    private readonly HttpClient _client;
    private readonly string _settingsPath;

    public TelemetrySwitchHost(string? settings = null)
    {
        _settingsPath = Path.Combine(_folder.Path, "settings.json");

        if (settings is not null)
        {
            File.WriteAllText(_settingsPath, settings);
        }

        _api = new StudioApiHost(
            events: null,
            traces: null,
            collector: null,
            clock: null,
            ("ClaudeSettings:Path", _settingsPath),
            ("ClaudeSettings:StampPath", Path.Combine(_folder.Path, StampName)),
            ("Collector:Address", Collector),
            ("Catalogue:Path", Path.Combine(_folder.Path, "no-catalogue")));

        _client = _api.CreateClient();
    }

    public HttpClient Client => _client;

    public Task<JsonElement> State() => _client.GetFromJsonAsync<JsonElement>("/api/telemetry/switch");

    public Task<HttpResponseMessage> Flip(bool emitting) =>
        _client.PutAsJsonAsync("/api/telemetry/switch", new { emitting }, Wire);

    public async Task<JsonElement> Turn(bool emitting)
    {
        using var response = await Flip(emitting);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    public bool SettingsExist() => File.Exists(_settingsPath);

    public string SettingsText() => File.ReadAllText(_settingsPath);

    public string SettingsName() => Path.GetFileName(_settingsPath);

    public string Beside(string name) => Path.Combine(_folder.Path, name);

    public IReadOnlyList<string> FilesWritten() =>
        [.. Directory.EnumerateFiles(_folder.Path).Select(Path.GetFileName).Order(StringComparer.Ordinal)!];

    // Windows will not replace a read-only file, which is the only way to make a write fail on purpose.
    public void Seal() => File.SetAttributes(_settingsPath, FileAttributes.ReadOnly);

    public void Unseal() => File.SetAttributes(_settingsPath, FileAttributes.Normal);

    public void WriteSettings(string settings) => File.WriteAllText(_settingsPath, settings);

    public static JsonElement TeamEnvironment(JsonElement state)
    {
        using var document = JsonDocument.Parse(state.GetProperty("team").GetProperty("text").GetString()!);

        return document.RootElement.GetProperty("env").Clone();
    }

    public void EditEnvironment(Action<JsonObject> edit)
    {
        var settings = JsonNode.Parse(SettingsText())!;
        edit(settings["env"]!.AsObject());

        File.WriteAllText(_settingsPath, settings.ToJsonString());
    }

    public JsonElement Settings() => JsonDocument.Parse(SettingsText()).RootElement.Clone();

    public string? Variable(string name)
    {
        var settings = Settings();

        return settings.TryGetProperty("env", out var environment)
            && environment.TryGetProperty(name, out var value)
                ? value.GetString()
                : null;
    }

    public void Dispose()
    {
        // A sealed file would stop the folder going away with it.
        if (File.Exists(_settingsPath))
        {
            Unseal();
        }

        _client.Dispose();
        _api.Dispose();
        _folder.Dispose();
    }
}
