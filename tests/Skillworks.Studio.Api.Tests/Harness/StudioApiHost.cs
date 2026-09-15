using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Provenance;

namespace Skillworks.Studio.Api.Tests.Harness;

public sealed class StudioApiHost(HttpMessageHandler events, params (string Key, string? Value)[] settings)
    : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration(configuration =>
            configuration.AddInMemoryCollection(settings.Select(s => new KeyValuePair<string, string?>(s.Key, s.Value))));

        // Only the handler is replaced, so Studio's real query, parsing, address and timeout stay under test.
        builder.ConfigureTestServices(services =>
            services.AddHttpClient(SkillEvents.ClientName).ConfigurePrimaryHttpMessageHandler(() => events));
    }
}
