using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Provenance;

namespace Skillworks.Studio.Api.Tests;

/// <summary>
/// The one test seam: the real API in memory, with only the outside world substituted.
/// Settings given here land in configuration exactly as the AppHost's environment would.
/// </summary>
public sealed class StudioApi(HttpMessageHandler events, params (string Key, string? Value)[] settings)
    : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration(configuration =>
            configuration.AddInMemoryCollection(settings.Select(s => new KeyValuePair<string, string?>(s.Key, s.Value))));

        // The events store is substituted at the HTTP boundary and nowhere above it, so the query
        // Studio builds and the answer it parses are both the real ones. Configuring the same named
        // client again only replaces its handler: the address and the timeout stay as Core set them.
        builder.ConfigureTestServices(services =>
            services.AddHttpClient(SkillEvents.ClientName).ConfigurePrimaryHttpMessageHandler(() => events));
    }
}
