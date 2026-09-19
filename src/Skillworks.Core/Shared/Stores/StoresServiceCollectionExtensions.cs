using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Http;
using Microsoft.Extensions.Options;
using Skillworks.Core.Shared.Stores.Collector;
using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Shared.Stores;

public static class StoresServiceCollectionExtensions
{
    public static IServiceCollection AddStores(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<LokiOptions>(configuration.GetSection(LokiOptions.SectionName));
        services.Configure<TempoOptions>(configuration.GetSection(TempoOptions.SectionName));
        services.Configure<CollectorOptions>(configuration.GetSection(CollectorOptions.SectionName));

        // Each registration that needs the clock adds it, so none has to trust another to.
        services.TryAddSingleton(TimeProvider.System);

        // A named client, not a typed one: a typed client held by a singleton keeps one handler for the app's life.
        services.AddHttpClient(EventsStoreReader.ClientName, (provider, client) =>
        {
            var loki = provider.GetRequiredService<IOptions<LokiOptions>>().Value;

            // No wait of its own: the reader waits a Patience on the Clock, which a busy machine cannot run out.
            client.BaseAddress = loki.ResolvedAddress();
        });

        // Its own address, because the two stores fall short apart from each other.
        services.AddHttpClient(TraceStoreReader.ClientName, (provider, client) =>
        {
            var tempo = provider.GetRequiredService<IOptions<TempoOptions>>().Value;

            client.BaseAddress = tempo.ResolvedAddress();
            client.Timeout = TimeSpan.FromSeconds(tempo.TimeoutSeconds);
        });

        services.AddHttpClient(CollectorReader.ClientName, (provider, client) =>
        {
            var collector = provider.GetRequiredService<IOptions<CollectorOptions>>().Value;

            client.BaseAddress = collector.ResolvedAddress();
            client.Timeout = TimeSpan.FromSeconds(collector.TimeoutSeconds);
        });

        // Cleared wholesale, so no retry a shell adds, now or later, turns a down container's fast 502 into a slow timeout.
        foreach (var clientName in new[] { EventsStoreReader.ClientName, TraceStoreReader.ClientName, CollectorReader.ClientName })
        {
            services.Configure<HttpClientFactoryOptions>(
                clientName,
                options => options.HttpMessageHandlerBuilderActions.Clear());
        }

        services.AddSingleton<EventsStoreReader>();
        services.AddSingleton<TraceStoreReader>();
        services.AddSingleton<CollectorReader>();

        return services;
    }
}
