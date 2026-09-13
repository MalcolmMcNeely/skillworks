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
    public Studio(string? transcriptPath, string? cataloguePath = null)
    {
        _api = new StudioApi(
            ("Transcripts:Path", transcriptPath),
            ("Telemetry:DatabasePath", Path.Combine(_data.Path, "telemetry.db")),
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

        while (await CompletedPasses() < passes)
        {
            if (DateTime.UtcNow > deadline)
            {
                throw new TimeoutException($"Ingest never reached pass {passes}.");
            }

            await Task.Delay(20);
        }
    }

    /// <summary>Asks for another pass and waits for it, so a test can prove what a re-read does.</summary>
    public async Task IngestAgain()
    {
        await WaitForIngestPasses(1);
        var passes = await CompletedPasses();

        using var response = await _client.PostAsync("/api/ingest", content: null);
        response.EnsureSuccessStatusCode();

        await WaitForIngestPasses(passes + 1);
    }

    public async Task<IReadOnlyList<SkillRow>> Skills()
    {
        await WaitForIngestPasses(1);

        return await _client.GetFromJsonAsync<SkillRow[]>("/api/skills", Wire) ?? [];
    }

    /// <summary>The one named skill. Fails the test if the table does not hold exactly one.</summary>
    public async Task<SkillRow> Skill(string name) =>
        (await Skills()).Single(skill => skill.Name == name);

    /// <summary>How often a skill fired, counting a skill the table never mentions as zero.</summary>
    public async Task<int> ActivationsOf(string name) =>
        (await Skills()).SingleOrDefault(skill => skill.Name == name)?.Activations ?? 0;

    public void Dispose()
    {
        _client.Dispose();
        _api.Dispose();

        // SQLite pools its connections, so the file stays open past the host and the directory
        // will not delete.
        SqliteConnection.ClearAllPools();
        _data.Dispose();
    }

    private async Task<int> CompletedPasses()
    {
        var status = await _client.GetFromJsonAsync<JsonElement>("/api/ingest");

        return status.GetProperty("completedPasses").GetInt32();
    }
}
