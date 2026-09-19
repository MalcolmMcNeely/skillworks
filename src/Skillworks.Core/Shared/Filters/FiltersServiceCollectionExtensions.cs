using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Shared.Filters;

public static class FiltersServiceCollectionExtensions
{
    public static IServiceCollection AddFilters(this IServiceCollection services)
    {
        // Each registration that needs the clock adds it, so none has to trust another to.
        services.TryAddSingleton(TimeProvider.System);

        // How far back a Filter may reach is a limit of the events store, so AddStores binds the day count.
        services.AddSingleton(provider => new Lookback(
            provider.GetRequiredService<IOptions<LokiOptions>>().Value.LookbackDays,
            provider.GetRequiredService<TimeProvider>()));
        services.AddSingleton<FilterChoices>();

        return services;
    }
}
