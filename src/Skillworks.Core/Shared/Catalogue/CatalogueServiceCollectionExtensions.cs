using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace Skillworks.Core.Shared.Catalogue;

public static class CatalogueServiceCollectionExtensions
{
    public static IServiceCollection AddCatalogue(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<CatalogueOptions>(configuration.GetSection(CatalogueOptions.SectionName));

        services.AddSingleton<CatalogueLocator>();
        services.AddSingleton<CatalogueSkills>();

        return services;
    }
}
