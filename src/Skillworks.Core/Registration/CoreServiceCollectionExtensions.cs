using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Arriving;
using Skillworks.Core.Catalogue;
using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;
using Skillworks.Core.Health;
using Skillworks.Core.Sessions;
using Skillworks.Core.Sessions.Queries;
using Skillworks.Core.Skills;
using Skillworks.Core.Spend.Queries;
using Skillworks.Core.Telemetry;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Registration;

public static class CoreServiceCollectionExtensions
{
    public static IServiceCollection AddSkillworksCore(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<CatalogueOptions>(configuration.GetSection(CatalogueOptions.SectionName));
        services.Configure<ClaudeSettingsOptions>(configuration.GetSection(ClaudeSettingsOptions.SectionName));
        services.Configure<LokiOptions>(configuration.GetSection(LokiOptions.SectionName));
        services.Configure<TempoOptions>(configuration.GetSection(TempoOptions.SectionName));

        services.TryAddSingleton(TimeProvider.System);

        services.AddSingleton<CatalogueLocator>();
        services.AddSingleton<CatalogueSkills>();
        services.AddSingleton(provider => new Lookback(
            provider.GetRequiredService<IOptions<LokiOptions>>().Value.LookbackDays,
            provider.GetRequiredService<TimeProvider>()));
        services.AddSingleton<ClaudeSettingsFile>();
        services.AddSingleton<TelemetrySwitch>();

        services.AddSingleton<ActivationQueries>();
        services.AddSingleton<SpendQueries>();
        services.AddSingleton<SessionQueries>();

        // A named client, not a typed one: a typed client held by a singleton keeps one handler for the app's life.
        services.AddHttpClient(EventsStoreReader.ClientName, (provider, client) =>
        {
            var loki = provider.GetRequiredService<IOptions<LokiOptions>>().Value;

            client.BaseAddress = loki.ResolvedAddress();
            client.Timeout = TimeSpan.FromSeconds(loki.TimeoutSeconds);
        });

        // Its own address and its own timeout: the two stores fall short apart from each other.
        services.AddHttpClient(TraceStoreReader.ClientName, (provider, client) =>
        {
            var tempo = provider.GetRequiredService<IOptions<TempoOptions>>().Value;

            client.BaseAddress = tempo.ResolvedAddress();
            client.Timeout = TimeSpan.FromSeconds(tempo.TimeoutSeconds);
        });

        // Cleared wholesale, so no retry a shell adds, now or later, turns a down container's fast 502 into a slow timeout.
        foreach (var store in new[] { EventsStoreReader.ClientName, TraceStoreReader.ClientName })
        {
            services.Configure<HttpClientFactoryOptions>(
                store,
                options => options.HttpMessageHandlerBuilderActions.Clear());
        }

        services.AddSingleton<EventsStoreReader>();
        services.AddSingleton<TraceStoreReader>();
        services.AddSingleton<GapReport>();
        services.AddSingleton<ArrivingDays>();
        services.AddSingleton<SkillReport>();
        services.AddSingleton<SessionReport>();
        services.AddSingleton<StudioHealth>();

        return services;
    }
}
