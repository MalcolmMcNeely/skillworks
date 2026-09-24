using System.Net.Http.Json;
using System.Text.Json;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Marketplace;

public sealed class MarketplaceEndpointsTests
{
    [Fact]
    public async Task Reports_the_configured_Marketplace_as_present_when_the_folder_is_there()
    {
        var folder = Directory.CreateTempSubdirectory("skillworks-marketplace");
        try
        {
            var body = await GetMarketplace(folder.FullName);

            Assert.Equal(folder.FullName, body.GetProperty("path").GetString());
            Assert.True(body.GetProperty("exists").GetBoolean());
        }
        finally
        {
            folder.Delete(recursive: true);
        }
    }

    [Fact]
    public async Task Reports_the_configured_Marketplace_as_absent_when_the_folder_is_missing()
    {
        var missing = Path.Combine(Path.GetTempPath(), $"skillworks-missing-{Guid.NewGuid():N}");

        var body = await GetMarketplace(missing);

        Assert.Equal(missing, body.GetProperty("path").GetString());
        Assert.False(body.GetProperty("exists").GetBoolean());
    }

    [Fact]
    public async Task Resolves_a_relative_Marketplace_path_to_an_absolute_one()
    {
        var body = await GetMarketplace("plugins");

        Assert.True(Path.IsPathFullyQualified(body.GetProperty("path").GetString()!));
    }

    private static async Task<JsonElement> GetMarketplace(string marketplacePath)
    {
        using var studio = new StudioHost(marketplacePath);

        return await studio.Client.GetFromJsonAsync<JsonElement>("/api/marketplace");
    }
}
