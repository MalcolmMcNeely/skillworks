using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Settings;
using Skillworks.Core.Skills;
using Skillworks.Core.Telemetry;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core;

/// <summary>One call that gives a shell the whole domain. The API uses it; the MCP server will too.</summary>
public static class CoreServiceCollectionExtensions
{
    public static IServiceCollection AddSkillworksCore(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<CatalogueOptions>(configuration.GetSection(CatalogueOptions.SectionName));
        services.Configure<TranscriptOptions>(configuration.GetSection(TranscriptOptions.SectionName));
        services.Configure<TelemetryOptions>(configuration.GetSection(TelemetryOptions.SectionName));
        services.Configure<ClaudeSettingsOptions>(configuration.GetSection(ClaudeSettingsOptions.SectionName));

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
        services.AddSingleton<ActivationStore>();
        services.AddSingleton<SkillReport>();

        // Order matters: the schema is in place before the first pass and before the first query.
        services.AddHostedService<TelemetrySchemaService>();
        services.AddHostedService<TranscriptIngestService>();

        return services;
    }
}
