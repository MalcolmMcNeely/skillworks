using System.Net.Http.Json;
using System.Text.Json;

namespace Skillworks.Studio.Api.Tests;

public sealed class TranscriptEndpointTests
{
    [Fact]
    public async Task Finds_the_transcripts_without_being_told_where_they_are()
    {
        using var studio = new Studio(transcriptPath: null);

        var body = await studio.Client.GetFromJsonAsync<JsonElement>("/api/transcripts");

        // Claude Code writes every session under the user's own .claude folder, so this is the one
        // place Studio never has to be told about.
        Assert.Equal(
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                ".claude",
                "projects"),
            body.GetProperty("path").GetString());
    }

    [Fact]
    public async Task Says_so_when_the_configured_transcript_folder_is_missing()
    {
        var missing = Path.Combine(Path.GetTempPath(), $"skillworks-missing-{Guid.NewGuid():N}");

        using var studio = new Studio(missing);
        var body = await studio.Client.GetFromJsonAsync<JsonElement>("/api/transcripts");

        Assert.Equal(missing, body.GetProperty("path").GetString());
        Assert.False(body.GetProperty("exists").GetBoolean());
    }
}
