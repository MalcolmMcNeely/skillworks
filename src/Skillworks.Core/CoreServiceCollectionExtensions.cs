using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Catalogue;

namespace Skillworks.Core;

/// <summary>One call that gives a shell the whole domain. The API uses it; the MCP server will too.</summary>
public static class CoreServiceCollectionExtensions
{
    public static IServiceCollection AddSkillworksCore(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<CatalogueOptions>(configuration.GetSection(CatalogueOptions.SectionName));
        services.AddSingleton<CatalogueLocator>();

        return services;
    }
}
