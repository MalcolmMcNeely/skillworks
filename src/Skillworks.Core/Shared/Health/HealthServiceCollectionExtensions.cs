using Microsoft.Extensions.DependencyInjection;

namespace Skillworks.Core.Shared.Health;

public static class HealthServiceCollectionExtensions
{
    public static IServiceCollection AddHealth(this IServiceCollection services)
    {
        services.AddSingleton<StudioHealth>();

        return services;
    }
}
