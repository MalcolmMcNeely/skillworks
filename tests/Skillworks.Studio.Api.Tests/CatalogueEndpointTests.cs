using System.Net.Http.Json;
using System.Text.Json;

namespace Skillworks.Studio.Api.Tests;

public sealed class CatalogueEndpointTests
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
        using var api = new StudioApi(Events.Holding(), ("Catalogue:Path", cataloguePath));
        using var client = api.CreateClient();

        return await client.GetFromJsonAsync<JsonElement>("/api/catalogue");
    }
}
