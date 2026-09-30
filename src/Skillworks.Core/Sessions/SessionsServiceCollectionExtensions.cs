using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using Skillworks.Core.Sessions.Lookup;
using Skillworks.Core.Sessions.Queries;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions;

public static class SessionsServiceCollectionExtensions
{
    public static IServiceCollection AddSessions(this IServiceCollection services)
    {
        // Each registration that needs the clock adds it, so none has to trust another to.
        services.TryAddSingleton(TimeProvider.System);

        // How far back a Lookup may reach is a cost of the events store, so AddStores binds the day count.
        services.AddSingleton(provider =>
            new LookupReach(provider.GetRequiredService<IOptions<LokiOptions>>().Value.LookupReachDays));

        services.AddSingleton<SessionQueries>();
        services.AddSingleton<StepQueries>();
        services.AddSingleton<AgentQueries>();

        services.AddSingleton<SessionReport>();
        services.AddSingleton<StepReport>();

        return services;
    }
}
