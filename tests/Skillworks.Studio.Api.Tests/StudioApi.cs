using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;

namespace Skillworks.Studio.Api.Tests;

/// <summary>
/// The one test seam: the real API in memory, with only the outside world substituted.
/// Settings given here land in configuration exactly as the AppHost's environment would.
/// </summary>
public sealed class StudioApi(params (string Key, string? Value)[] settings) : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder) =>
        builder.ConfigureAppConfiguration(configuration =>
            configuration.AddInMemoryCollection(settings.Select(s => new KeyValuePair<string, string?>(s.Key, s.Value))));
}
