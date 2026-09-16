using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Telemetry;

public sealed class TelemetrySwitchHost : IDisposable
{
    public const string Collector = "http://localhost:4318";

    private static readonly JsonSerializerOptions Wire = new(JsonSerializerDefaults.Web);

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
            clock: null,
            ("ClaudeSettings:Path", _settingsPath),
            ("ClaudeSettings:StampPath", Path.Combine(_folder.Path, "telemetry-switch.json")),
            ("ClaudeSettings:CollectorEndpoint", Collector),
            ("Catalogue:Path", Path.Combine(_folder.Path, "no-catalogue")));

        _client = _api.CreateClient();
    }

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
        _folder.Dispose();
    }
}
