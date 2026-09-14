using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Data.Sqlite;
using Skillworks.Core.Settings;

namespace Skillworks.Studio.Api.Tests;

public sealed record SkillsAnswer
{
    public required SkillRow[] Skills { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}

// Required, so a field renamed in the API fails the deserialize rather than quietly reading as zero.
public sealed record SkillRow
{
    public required string Name { get; init; }

    public required int Activations { get; init; }

    public required string[] Repositories { get; init; }

    public required string[] Branches { get; init; }

    public required string[] Models { get; init; }

    public required string[] Efforts { get; init; }

    public required SpendRow Spend { get; init; }

    public required decimal AverageCost { get; init; }

    public required OriginRow[] Origins { get; init; }
}

public sealed record OriginRow
{
    public required string? Trigger { get; init; }

    public required string? Source { get; init; }

    public required string? Plugin { get; init; }

    public required string? Marketplace { get; init; }
}

public sealed record ProvenanceRow
{
    public required string Gap { get; init; }

    public required string? Missing { get; init; }

    public required DateTimeOffset SinceUtc { get; init; }
}

public sealed record HealthRow
{
    public required PartRow[] Parts { get; init; }

    public required string? WhyEmpty { get; init; }
}

public sealed record PartRow
{
    public required string Name { get; init; }

    public required string State { get; init; }

    public required string Detail { get; init; }

    public required string? Action { get; init; }
}

public sealed record SpendRow
{
    public required long InputTokens { get; init; }

    public required long OutputTokens { get; init; }

    public required long ThinkingTokens { get; init; }

    public required long CacheReadTokens { get; init; }

    public required long CacheWriteTokens { get; init; }

    public required decimal Cost { get; init; }

    public required bool CostIsPartial { get; init; }
}

public sealed record FilterChoiceRow
{
    public required string[] Repositories { get; init; }

    public required string[] Skills { get; init; }
}

public sealed record PriceRow
{
    public required string Model { get; init; }

    public required decimal InputPerMillion { get; init; }

    public required decimal OutputPerMillion { get; init; }

    public required decimal CacheReadPerMillion { get; init; }

    public required decimal CacheWrite5mPerMillion { get; init; }

    public required decimal CacheWrite1hPerMillion { get; init; }
}

public sealed record IngestRow
{
    public required bool Running { get; init; }

    public required int CompletedPasses { get; init; }

    public required int TranscriptsSeen { get; init; }

    public required int TranscriptsTotal { get; init; }

    public required int TranscriptsRead { get; init; }

    public required int ActivationsAdded { get; init; }

    public required bool LastPassWasFull { get; init; }

    public required DateTimeOffset? LastRefreshUtc { get; init; }

    public required int Faults { get; init; }
}

public sealed record ActivationsAnswer
{
    public required ActivationRow[] Activations { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}

public sealed record ActivationRow
{
    public required string Id { get; init; }

    public required string Skill { get; init; }

    public required string? Repository { get; init; }

    public required string? Branch { get; init; }

    public required string? Model { get; init; }

    public required string? Effort { get; init; }

    public required DateTimeOffset TimestampUtc { get; init; }

    public required OriginRow? Origin { get; init; }
}

public sealed record ActivationAnswer
{
    public required ActivationDetailRow Activation { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}

public sealed record ActivationDetailRow
{
    public required string Id { get; init; }

    public required string Skill { get; init; }

    public required string SessionId { get; init; }

    public required string? Repository { get; init; }

    public required string? Branch { get; init; }

    public required string? Model { get; init; }

    public required string? Effort { get; init; }

    public required DateTimeOffset TimestampUtc { get; init; }

    public required ArgumentRow[] Arguments { get; init; }

    public required OriginRow? Origin { get; init; }
}

public sealed record ArgumentRow
{
    public required string Name { get; init; }

    public required string Value { get; init; }
}

public sealed record FaultRow
{
    public required string Path { get; init; }

    public required long Line { get; init; }

    public required string Reason { get; init; }

    public required DateTimeOffset NoticedUtc { get; init; }
}

public sealed class Studio : IDisposable
{
    private static readonly JsonSerializerOptions Wire = new(JsonSerializerDefaults.Web);

    // Shares the switch's list, so this fixture cannot claim telemetry is on while Studio reads it as off.
    private static readonly string EmittingSettings = new JsonObject
    {
        ["env"] = new JsonObject(
            TelemetryVariables
                .For(new ClaudeSettingsOptions().CollectorEndpoint)
                .Select(variable => KeyValuePair.Create(variable.Key, (JsonNode?)JsonValue.Create(variable.Value)))),
    }.ToJsonString();

    private readonly TemporaryFolder _data = new();
    private readonly StudioApi _api;
    private readonly HttpClient _client;

    public Studio(
        string? transcriptPath,
        string? cataloguePath = null,
        // Zero, so no pass runs that a test did not ask for and the pass counts tests wait on stay exact.
        int sweepSeconds = 0,
        Events? events = null,
        int maxEvents = 5000,
        // Not the developer's settings, or provenance tests would pass or fail on this machine's telemetry.
        bool emitting = true,
        string? settings = null)
    {
        var settingsPath = Path.Combine(_data.Path, "settings.json");
        File.WriteAllText(settingsPath, settings ?? (emitting ? EmittingSettings : "{}"));

        _api = new StudioApi(
            events ?? Events.Holding(),
            ("Transcripts:Path", transcriptPath),
            ("Telemetry:DatabasePath", Path.Combine(_data.Path, "telemetry.db")),
            ("Telemetry:SweepSeconds", sweepSeconds.ToString()),
            ("Loki:MaxEvents", maxEvents.ToString()),
            ("ClaudeSettings:Path", settingsPath),
            ("ClaudeSettings:StampPath", Path.Combine(_data.Path, "telemetry-switch.json")),
            ("Catalogue:Path", cataloguePath ?? Path.Combine(_data.Path, "no-catalogue")));

        _client = _api.CreateClient();
    }

    public HttpClient Client => _client;

    public static string Fixture(string name) => Path.Combine(AppContext.BaseDirectory, "Transcripts", name);

    public static string Catalogue() => Path.Combine(AppContext.BaseDirectory, "Catalogue");

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

    public async Task<IngestRow> Ask(string route)
    {
        await WaitForIngestPasses(1);

        using var response = await _client.PostAsync(route, content: null);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<IngestRow>(Wire)
            ?? throw new InvalidOperationException("The ingest status came back empty.");
    }

    public async Task<HealthRow> Health()
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<HealthRow>("/api/health", Wire)
            ?? throw new InvalidOperationException("The health report came back empty.");
    }

    public async Task<PartRow> Part(string name) =>
        (await Health()).Parts.Single(part => part.Name == name);

    public async Task<IReadOnlyList<FaultRow>> Faults()
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<FaultRow[]>("/api/ingest/faults", Wire) ?? [];
    }

    public async Task<IReadOnlyList<SkillRow>> Skills(string filter = "") => (await SkillTable(filter)).Skills;

    public async Task<SkillsAnswer> SkillTable(string filter = "")
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<SkillsAnswer>($"/api/skills{filter}", Wire)
            ?? throw new InvalidOperationException("The skill table came back empty.");
    }

    public async Task<HttpResponseMessage> AskForSkills(string filter)
    {
        await WaitForIngestPasses(1);

        return await _client.GetAsync($"/api/skills{filter}");
    }

    public async Task<SkillRow> Skill(string name, string filter = "") =>
        (await Skills(filter)).Single(skill => skill.Name == name);

    public async Task<int> ActivationsOf(string name, string filter = "") =>
        (await Skills(filter)).SingleOrDefault(skill => skill.Name == name)?.Activations ?? 0;

    public async Task<IReadOnlyList<ActivationRow>> Activations(string filter = "") =>
        (await ActivationList(filter)).Activations;

    public async Task<ActivationsAnswer> ActivationList(string filter = "")
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<ActivationsAnswer>($"/api/activations{filter}", Wire)
            ?? throw new InvalidOperationException("The activation list came back empty.");
    }

    public async Task<ActivationDetailRow> Activation(string id) => (await OpenActivation(id)).Activation;

    public async Task<ActivationAnswer> OpenActivation(string id)
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<ActivationAnswer>($"/api/activations/{id}", Wire)
            ?? throw new InvalidOperationException("The activation came back empty.");
    }

    public async Task<HttpResponseMessage> AskForActivation(string id)
    {
        await WaitForIngestPasses(1);

        return await _client.GetAsync($"/api/activations/{id}");
    }

    public async Task<FilterChoiceRow> Filters()
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<FilterChoiceRow>("/api/filters", Wire)
            ?? throw new InvalidOperationException("The filter choices came back empty.");
    }

    public async Task<IReadOnlyList<PriceRow>> Prices()
    {
        return await _client.GetFromJsonAsync<PriceRow[]>("/api/prices", Wire) ?? [];
    }

    public async Task Reprice(PriceRow price)
    {
        using var response = await _client.PutAsJsonAsync("/api/prices", price, Wire);
        response.EnsureSuccessStatusCode();
    }

    public async Task WaitForSkill(string name)
    {
        var deadline = DateTime.UtcNow.AddSeconds(30);

        while (await ActivationsOf(name) == 0)
        {
            if (DateTime.UtcNow > deadline)
            {
                throw new TimeoutException($"{name} never appeared.");
            }

            await Task.Delay(50);
        }
    }

    public void Dispose()
    {
        _client.Dispose();
        _api.Dispose();

        // SQLite pools its connections, so the file stays open past the host and the directory
        // will not delete.
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
