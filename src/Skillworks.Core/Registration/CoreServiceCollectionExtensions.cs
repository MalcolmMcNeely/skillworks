using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Skillworks.Core.Activations;
using Skillworks.Core.Activations.Stores;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Health;
using Skillworks.Core.Ingest;
using Skillworks.Core.Ingest.Stores;
using Skillworks.Core.Provenance;
using Skillworks.Core.Skills;
using Skillworks.Core.Spend;
using Skillworks.Core.Spend.Stores;
using Skillworks.Core.Telemetry;
using Skillworks.Core.TelemetryStore;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Registration;

public static class CoreServiceCollectionExtensions
{
    public static IServiceCollection AddSkillworksCore(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<CatalogueOptions>(configuration.GetSection(CatalogueOptions.SectionName));
        services.Configure<TranscriptOptions>(configuration.GetSection(TranscriptOptions.SectionName));
        services.Configure<TelemetryOptions>(configuration.GetSection(TelemetryOptions.SectionName));
        services.Configure<ClaudeSettingsOptions>(configuration.GetSection(ClaudeSettingsOptions.SectionName));
        services.Configure<LokiOptions>(configuration.GetSection(LokiOptions.SectionName));

        services.TryAddSingleton(TimeProvider.System);

        services.AddSingleton<CatalogueLocator>();
        services.AddSingleton<CatalogueSkills>();
        services.AddSingleton<TranscriptLocator>();
        services.AddSingleton<RepositoryNames>();
        services.AddSingleton<ClaudeSettingsFile>();
        services.AddSingleton<TelemetrySwitch>();

        services.AddDbContextFactory<TelemetryDbContext>((provider, builder) =>
        {
            var path = provider.GetRequiredService<IOptions<TelemetryOptions>>().Value.ResolvedDatabasePath();
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            builder.UseSqlite($"Data Source={path}");
        });

        services.AddSingleton<TranscriptIngestor>();
        services.AddSingleton<IngestState>();
        services.AddSingleton<TranscriptFaultStore>();
        services.AddSingleton<IngestReport>();
        services.AddSingleton<ActivationStore>();
        services.AddSingleton<SpendStore>();
        services.AddSingleton<PriceTable>();

        // A named client rather than a typed one: everything else here is a singleton, and a typed
        // client held by one would keep a single handler for the life of the app.
        services.AddHttpClient(SkillEvents.ClientName, (provider, client) =>
        {
            var loki = provider.GetRequiredService<IOptions<LokiOptions>>().Value;

            client.BaseAddress = loki.ResolvedAddress();
            client.Timeout = TimeSpan.FromSeconds(loki.TimeoutSeconds);
        });

        // A shell hands every outbound client retries and a long total timeout. This one read wants
        // neither: the screen already holds the transcript half, and three more attempts at a
        // container that is down turn a fast answer into a slow one that says less — a retried 502
        // comes back as a timeout, which is a worse thing to put on a screen. Everything is cleared
        // rather than one named handler removed, so the rule holds whatever a shell adds later.
        services.Configure<HttpClientFactoryOptions>(
            SkillEvents.ClientName,
            options => options.HttpMessageHandlerBuilderActions.Clear());

        services.AddSingleton<SkillEvents>();
        services.AddSingleton<ProvenanceReport>();
        services.AddSingleton<SkillReport>();
        services.AddSingleton<ActivationReport>();
        services.AddSingleton<StudioHealth>();

        // Order matters: the schema is in place before the first pass and before the first query.
        services.AddHostedService<TelemetrySchemaService>();
        services.AddHostedService<TranscriptIngestService>();

        return services;
    }
}
