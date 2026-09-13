using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace Skillworks.Studio.Api.Tests;

/// <summary>
/// One running Studio for one test: the real API in memory, a real SQLite file in a temporary
/// directory, and a checked-in fixture folder standing in for the machine's transcripts.
/// </summary>
public sealed class Studio : IDisposable
{
    private readonly DirectoryInfo _dataDirectory = Directory.CreateTempSubdirectory("skillworks-studio");
    private readonly StudioApi _api;
    private readonly HttpClient _client;

    /// <param name="transcriptPath">Null leaves the setting out, so Studio falls back to its default.</param>
    public Studio(string? transcriptPath, string? cataloguePath = null)
    {
        _api = new StudioApi(
            ("Transcripts:Path", transcriptPath),
            ("Telemetry:DatabasePath", Path.Combine(_dataDirectory.FullName, "telemetry.db")),
            ("Catalogue:Path", cataloguePath ?? Path.Combine(_dataDirectory.FullName, "no-catalogue")));

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
    public async Task<JsonElement> WaitForIngestPasses(int passes)
    {
        var deadline = DateTime.UtcNow.AddSeconds(30);

        while (true)
        {
            var status = await _client.GetFromJsonAsync<JsonElement>("/api/ingest");

            if (status.GetProperty("completedPasses").GetInt32() >= passes)
            {
                return status;
            }

            if (DateTime.UtcNow > deadline)
            {
                throw new TimeoutException($"Ingest never reached pass {passes}. Last status: {status}");
            }

            await Task.Delay(20);
        }
    }

    /// <summary>Asks for another pass and waits for it, so a test can prove what a re-read does.</summary>
    public async Task IngestAgain()
    {
        var before = await WaitForIngestPasses(1);
        var passes = before.GetProperty("completedPasses").GetInt32();

        using var response = await _client.PostAsync("/api/ingest", content: null);
        response.EnsureSuccessStatusCode();

        await WaitForIngestPasses(passes + 1);
    }

    public async Task<JsonElement> GetSkills()
    {
        await WaitForIngestPasses(1);
        return await _client.GetFromJsonAsync<JsonElement>("/api/skills");
    }

    public void Dispose()
    {
        _client.Dispose();
        _api.Dispose();

        // SQLite pools its connections, so the file stays open past the host and the directory
        // will not delete.
        SqliteConnection.ClearAllPools();
        _dataDirectory.Delete(recursive: true);
    }
}
