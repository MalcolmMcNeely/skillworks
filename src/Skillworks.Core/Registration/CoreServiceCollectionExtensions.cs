using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Skillworks.Core.Activations;
using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Catalogue;
using Skillworks.Core.EventsStore;
using Skillworks.Core.Health;
using Skillworks.Core.Ingest;
using Skillworks.Core.Ingest.Queries;
using Skillworks.Core.Provenance;
using Skillworks.Core.Skills;
using Skillworks.Core.Spend;
using Skillworks.Core.Spend.Queries;
using Skillworks.Core.Telemetry;
using Skillworks.Core.TranscriptStore;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Registration;

public static class CoreServiceCollectionExtensions
{
    public static IServiceCollection AddSkillworksCore(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<CatalogueOptions>(configuration.GetSection(CatalogueOptions.SectionName));
        services.Configure<TranscriptOptions>(configuration.GetSection(TranscriptOptions.SectionName));
        services.Configure<TranscriptStoreOptions>(configuration.GetSection(TranscriptStoreOptions.SectionName));
        services.Configure<ClaudeSettingsOptions>(configuration.GetSection(ClaudeSettingsOptions.SectionName));
        services.Configure<LokiOptions>(configuration.GetSection(LokiOptions.SectionName));

        services.TryAddSingleton(TimeProvider.System);

        services.AddSingleton<CatalogueLocator>();
        services.AddSingleton<CatalogueSkills>();
        services.AddSingleton<TranscriptLocator>();
        services.AddSingleton<RepositoryNames>();
        services.AddSingleton<ClaudeSettingsFile>();
        services.AddSingleton<TelemetrySwitch>();

        services.AddDbContextFactory<TranscriptStoreDbContext>((provider, builder) =>
        {
            var path = provider.GetRequiredService<IOptions<TranscriptStoreOptions>>().Value.ResolvedDatabasePath();
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            builder.UseSqlite($"Data Source={path}");
        });

        services.AddSingleton<TranscriptIngestor>();
        services.AddSingleton<IngestState>();
        services.AddSingleton<TranscriptFaultQueries>();
        services.AddSingleton<IngestReport>();
        services.AddSingleton<ActivationQueries>();
        services.AddSingleton<SpendQueries>();
        services.AddSingleton<PriceTable>();

        // A named client, not a typed one: a typed client held by a singleton keeps one handler for the app's life.
        services.AddHttpClient(EventsStoreReader.ClientName, (provider, client) =>
        {
            var loki = provider.GetRequiredService<IOptions<LokiOptions>>().Value;

            client.BaseAddress = loki.ResolvedAddress();
            client.Timeout = TimeSpan.FromSeconds(loki.TimeoutSeconds);
        });

        // Cleared wholesale, so no retry a shell adds, now or later, turns a down container's fast 502 into a slow timeout.
        services.Configure<HttpClientFactoryOptions>(
            EventsStoreReader.ClientName,
            options => options.HttpMessageHandlerBuilderActions.Clear());

        services.AddSingleton<EventsStoreReader>();
        services.AddSingleton<ProvenanceReport>();
        services.AddSingleton<SkillReport>();
        services.AddSingleton<ActivationReport>();
        services.AddSingleton<StudioHealth>();

        // Order matters: the schema is in place before the first pass and before the first query.
        services.AddHostedService<TranscriptStoreSchemaService>();
        services.AddHostedService<TranscriptIngestService>();

        return services;
    }
}
