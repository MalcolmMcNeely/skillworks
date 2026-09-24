using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace Skillworks.Core.Shared.Marketplace;

public static class MarketplaceServiceCollectionExtensions
{
    public static IServiceCollection AddMarketplace(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<MarketplaceOptions>(configuration.GetSection(MarketplaceOptions.SectionName));

        services.AddSingleton<MarketplaceLocator>();
        services.AddSingleton<MarketplaceSkills>();

        return services;
    }
}
