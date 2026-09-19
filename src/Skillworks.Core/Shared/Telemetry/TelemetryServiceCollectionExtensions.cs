using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace Skillworks.Core.Shared.Telemetry;

public static class TelemetryServiceCollectionExtensions
{
    public static IServiceCollection AddTelemetry(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<ClaudeSettingsOptions>(configuration.GetSection(ClaudeSettingsOptions.SectionName));

        services.AddSingleton<ClaudeSettingsFile>();
        services.AddSingleton<TelemetrySwitch>();

        return services;
    }
}
