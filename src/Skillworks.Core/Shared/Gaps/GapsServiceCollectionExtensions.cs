using Microsoft.Extensions.DependencyInjection;

namespace Skillworks.Core.Shared.Gaps;

public static class GapsServiceCollectionExtensions
{
    public static IServiceCollection AddGaps(this IServiceCollection services)
    {
        services.AddSingleton<GapReport>();

        return services;
    }
}
