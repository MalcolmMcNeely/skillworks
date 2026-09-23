using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Dashboard.Activations;
using Skillworks.Core.Dashboard.Activations.Queries;
using Skillworks.Core.Dashboard.Skills;
using Skillworks.Core.Dashboard.Spend.Queries;

namespace Skillworks.Core.Dashboard;

public static class DashboardServiceCollectionExtensions
{
    public static IServiceCollection AddDashboard(this IServiceCollection services)
    {
        services.AddSingleton<ActivationQueries>();
        services.AddSingleton<SpendQueries>();

        services.AddSingleton<SkillReport>();
        services.AddSingleton<ActivationReport>();

        return services;
    }
}
