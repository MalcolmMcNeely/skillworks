using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Watch.Activations;
using Skillworks.Core.Watch.Activations.Queries;
using Skillworks.Core.Watch.Skills;
using Skillworks.Core.Watch.Spend.Queries;

namespace Skillworks.Core.Watch;

public static class WatchServiceCollectionExtensions
{
    public static IServiceCollection AddWatch(this IServiceCollection services)
    {
        services.AddSingleton<ActivationQueries>();
        services.AddSingleton<SpendQueries>();

        services.AddSingleton<SkillReport>();
        services.AddSingleton<ActivationReport>();

        return services;
    }
}
