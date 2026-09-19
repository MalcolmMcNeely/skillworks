using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Skillworks.Core.Sessions.Queries;
using Skillworks.Core.Sessions.Steps;

namespace Skillworks.Core.Sessions;

public static class SessionsServiceCollectionExtensions
{
    public static IServiceCollection AddSessions(this IServiceCollection services)
    {
        // Each registration that needs the clock adds it, so none has to trust another to.
        services.TryAddSingleton(TimeProvider.System);

        services.AddSingleton<SessionQueries>();
        services.AddSingleton<StepQueries>();
        services.AddSingleton<AgentQueries>();
        services.AddSingleton<DepthQueries>();

        services.AddSingleton<SessionReport>();
        services.AddSingleton<StepReport>();

        return services;
    }
}
