using System.Net.Http.Json;
using System.Text.Json;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Catalogue;

public sealed class CatalogueEndpointsTests
{
    [Fact]
    public async Task Reports_the_configured_catalogue_as_present_when_the_folder_is_there()
    {
        var folder = Directory.CreateTempSubdirectory("skillworks-catalogue");
        try
        {
            var body = await GetCatalogue(folder.FullName);

            Assert.Equal(folder.FullName, body.GetProperty("path").GetString());
            Assert.True(body.GetProperty("exists").GetBoolean());
        }
        finally
        {
            folder.Delete(recursive: true);
        }
    }

    [Fact]
    public async Task Reports_the_configured_catalogue_as_absent_when_the_folder_is_missing()
    {
        var missing = Path.Combine(Path.GetTempPath(), $"skillworks-missing-{Guid.NewGuid():N}");

        var body = await GetCatalogue(missing);

        Assert.Equal(missing, body.GetProperty("path").GetString());
        Assert.False(body.GetProperty("exists").GetBoolean());
    }

    [Fact]
    public async Task Resolves_a_relative_catalogue_path_to_an_absolute_one()
    {
        var body = await GetCatalogue("plugins");

        Assert.True(Path.IsPathFullyQualified(body.GetProperty("path").GetString()!));
    }

    private static async Task<JsonElement> GetCatalogue(string cataloguePath)
    {
        // A folder that is not there, because the first ingest pass would otherwise read the developer's own transcripts.
        var noTranscripts = Path.Combine(Path.GetTempPath(), $"skillworks-missing-{Guid.NewGuid():N}");
        using var studio = new StudioHost(noTranscripts, cataloguePath);

        return await studio.Client.GetFromJsonAsync<JsonElement>("/api/catalogue");
    }
}
