using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace Skillworks.Studio.Api.Tests;

/// <summary>
/// One row of <c>GET /api/skills</c>. Every property is required, so a renamed field in the API
/// fails the deserialize rather than quietly reading as zero.
/// </summary>
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
}

/// <summary>What one skill cost, as the skill table reports it.</summary>
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

/// <summary><c>GET /api/filters</c>: the values the three filters can be narrowed to.</summary>
public sealed record FilterChoiceRow
{
    public required string[] Repositories { get; init; }

    public required string[] Skills { get; init; }
}

/// <summary>One row of <c>GET /api/prices</c>: what a million tokens costs on one model.</summary>
public sealed record PriceRow
{
    public required string Model { get; init; }

    public required decimal InputPerMillion { get; init; }

    public required decimal OutputPerMillion { get; init; }

    public required decimal CacheReadPerMillion { get; init; }

    public required decimal CacheWrite5mPerMillion { get; init; }

    public required decimal CacheWrite1hPerMillion { get; init; }
}

/// <summary><c>GET /api/ingest</c>: how far the ingest has got and how stale the numbers are.</summary>
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

/// <summary>One row of <c>GET /api/activations</c>: one firing, enough of it to pick one out.</summary>
public sealed record ActivationRow
{
    public required string Id { get; init; }

    public required string Skill { get; init; }

    public required string? Repository { get; init; }

    public required string? Branch { get; init; }

    public required string? Model { get; init; }

    public required string? Effort { get; init; }

    public required DateTimeOffset TimestampUtc { get; init; }
}

/// <summary><c>GET /api/activations/{id}</c>: one firing, with what it was called with.</summary>
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
}

/// <summary>One thing a skill was called with, as the transcript recorded it.</summary>
public sealed record ArgumentRow
{
    public required string Name { get; init; }

    public required string Value { get; init; }
}

/// <summary>One row of <c>GET /api/ingest/faults</c>: something the ingest had to step over.</summary>
public sealed record FaultRow
{
    public required string Path { get; init; }

    public required long Line { get; init; }

    public required string Reason { get; init; }

    public required DateTimeOffset NoticedUtc { get; init; }
}

/// <summary>
/// One running Studio for one test: the real API in memory, a real SQLite file in a temporary
/// directory, and a checked-in fixture folder standing in for the machine's transcripts.
/// </summary>
public sealed class Studio : IDisposable
{
    private static readonly JsonSerializerOptions Wire = new(JsonSerializerDefaults.Web);

    private readonly TemporaryFolder _data = new();
    private readonly StudioApi _api;
    private readonly HttpClient _client;

    /// <param name="transcriptPath">Null leaves the setting out, so Studio falls back to its default.</param>
    /// <param name="sweepSeconds">
    /// Zero, so no pass happens that the test did not ask for. Counting passes is how these tests
    /// stay off the flake list, and a sweep on a clock would make the count meaningless.
    /// </param>
    public Studio(string? transcriptPath, string? cataloguePath = null, int sweepSeconds = 0)
    {
        _api = new StudioApi(
            ("Transcripts:Path", transcriptPath),
            ("Telemetry:DatabasePath", Path.Combine(_data.Path, "telemetry.db")),
            ("Telemetry:SweepSeconds", sweepSeconds.ToString()),
            ("Catalogue:Path", cataloguePath ?? Path.Combine(_data.Path, "no-catalogue")));

        _client = _api.CreateClient();
    }

    public HttpClient Client => _client;

    /// <summary>Fixture folders live beside the test assembly, copied there by the build.</summary>
    public static string Fixture(string name) => Path.Combine(AppContext.BaseDirectory, "Transcripts", name);

    /// <summary>A fixture catalogue: one plugin, one skill that fires and one that never does.</summary>
    public static string Catalogue() => Path.Combine(AppContext.BaseDirectory, "Catalogue");

    /// <summary>
    /// Blocks until the background service has finished <paramref name="passes"/> ingest passes.
    /// Waiting on the count rather than on a clock is what keeps these tests off the flake list.
    /// </summary>
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

    /// <summary>Asks for another pass and waits for it, so a test can prove what a re-read does.</summary>
    public Task IngestAgain() => AskAndWait("/api/ingest");

    /// <summary>Throws away everything already read and waits for the re-read to finish.</summary>
    public Task FullIngest() => AskAndWait("/api/ingest/full");

    /// <summary>Asks for a pass without waiting, so a test can see what the ask itself reports.</summary>
    public async Task<IngestRow> Ask(string route)
    {
        await WaitForIngestPasses(1);

        using var response = await _client.PostAsync(route, content: null);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<IngestRow>(Wire)
            ?? throw new InvalidOperationException("The ingest status came back empty.");
    }

    public async Task<IReadOnlyList<FaultRow>> Faults()
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<FaultRow[]>("/api/ingest/faults", Wire) ?? [];
    }

    /// <param name="filter">A query string, leading <c>?</c> and all. Empty asks about everything.</param>
    public async Task<IReadOnlyList<SkillRow>> Skills(string filter = "")
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<SkillRow[]>($"/api/skills{filter}", Wire) ?? [];
    }

    /// <summary>The skills call as it came back, so a test can assert the status as well as the rows.</summary>
    public async Task<HttpResponseMessage> AskForSkills(string filter)
    {
        await WaitForIngestPasses(1);

        return await _client.GetAsync($"/api/skills{filter}");
    }

    /// <summary>The one named skill. Fails the test if the table does not hold exactly one.</summary>
    public async Task<SkillRow> Skill(string name, string filter = "") =>
        (await Skills(filter)).Single(skill => skill.Name == name);

    /// <summary>How often a skill fired, counting a skill the table never mentions as zero.</summary>
    public async Task<int> ActivationsOf(string name, string filter = "") =>
        (await Skills(filter)).SingleOrDefault(skill => skill.Name == name)?.Activations ?? 0;

    /// <param name="filter">A query string, leading <c>?</c> and all. Empty asks about everything.</param>
    public async Task<IReadOnlyList<ActivationRow>> Activations(string filter = "")
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<ActivationRow[]>($"/api/activations{filter}", Wire) ?? [];
    }

    /// <summary>One firing opened by its id, which is how the front end reaches a detail page.</summary>
    public async Task<ActivationDetailRow> Activation(string id)
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<ActivationDetailRow>($"/api/activations/{id}", Wire)
            ?? throw new InvalidOperationException("The activation came back empty.");
    }

    /// <summary>The detail call as it came back, so a test can assert the status of a bad id.</summary>
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

    /// <summary>Sets one model's price, which is the whole point of a table read at query time.</summary>
    public async Task Reprice(PriceRow price)
    {
        using var response = await _client.PutAsJsonAsync("/api/prices", price, Wire);
        response.EnsureSuccessStatusCode();
    }

    /// <summary>Waits for a skill to turn up on its own, for the sweep that nobody asked for.</summary>
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
