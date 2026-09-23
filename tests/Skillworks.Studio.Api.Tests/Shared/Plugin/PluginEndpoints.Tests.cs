using System.Net.Http.Json;
using System.Text.Json;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Plugin;

public sealed class PluginEndpointsTests
{
    [Fact]
    public async Task Reports_the_configured_plugin_as_present_when_the_folder_is_there()
    {
        var folder = Directory.CreateTempSubdirectory("skillworks-plugin");
        try
        {
            var body = await GetPlugin(folder.FullName);

            Assert.Equal(folder.FullName, body.GetProperty("path").GetString());
            Assert.True(body.GetProperty("exists").GetBoolean());
        }
        finally
        {
            folder.Delete(recursive: true);
        }
    }

    [Fact]
    public async Task Reports_the_configured_plugin_as_absent_when_the_folder_is_missing()
    {
        var missing = Path.Combine(Path.GetTempPath(), $"skillworks-missing-{Guid.NewGuid():N}");

        var body = await GetPlugin(missing);

        Assert.Equal(missing, body.GetProperty("path").GetString());
        Assert.False(body.GetProperty("exists").GetBoolean());
    }

    [Fact]
    public async Task Resolves_a_relative_plugin_path_to_an_absolute_one()
    {
        var body = await GetPlugin("plugins");

        Assert.True(Path.IsPathFullyQualified(body.GetProperty("path").GetString()!));
    }

    private static async Task<JsonElement> GetPlugin(string pluginPath)
    {
        using var studio = new StudioHost(pluginPath);

        return await studio.Client.GetFromJsonAsync<JsonElement>("/api/plugin");
    }
}
