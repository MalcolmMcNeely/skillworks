using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.EventsStore;
using Skillworks.Core.TraceStore;

namespace Skillworks.Studio.Api.Tests.Harness;

public sealed class StudioApiHost(
    HttpMessageHandler? events,
    HttpMessageHandler? traces,
    TimeProvider? clock,
    params (string Key, string? Value)[] settings)
    : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration(configuration =>
            configuration.AddInMemoryCollection(settings.Select(s => new KeyValuePair<string, string?>(s.Key, s.Value))));

        builder.ConfigureTestServices(services =>
        {
            // Only the handler is replaced, so Studio's real address and timeout stay under test.
            if (events is not null)
            {
                services.AddHttpClient(EventsStoreReader.ClientName).ConfigurePrimaryHttpMessageHandler(() => events);
            }

            if (traces is not null)
            {
                services.AddHttpClient(TraceStoreReader.ClientName).ConfigurePrimaryHttpMessageHandler(() => traces);
            }

            if (clock is not null)
            {
                services.AddSingleton<TimeProvider>(clock);
            }
        });
    }
}
