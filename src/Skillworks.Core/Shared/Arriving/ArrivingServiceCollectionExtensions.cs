using Microsoft.Extensions.DependencyInjection;

namespace Skillworks.Core.Shared.Arriving;

public static class ArrivingServiceCollectionExtensions
{
    public static IServiceCollection AddArriving(this IServiceCollection services)
    {
        services.AddSingleton<ArrivingDays>();

        return services;
    }
}
