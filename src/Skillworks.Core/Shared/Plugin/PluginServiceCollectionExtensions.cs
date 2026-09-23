using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace Skillworks.Core.Shared.Plugin;

public static class PluginServiceCollectionExtensions
{
    public static IServiceCollection AddPlugin(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<PluginOptions>(configuration.GetSection(PluginOptions.SectionName));

        services.AddSingleton<PluginLocator>();
        services.AddSingleton<PluginSkills>();

        return services;
    }
}
