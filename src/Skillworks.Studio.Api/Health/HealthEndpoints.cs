using Skillworks.Core.Health;

namespace Skillworks.Studio.Api.Health;

public static class HealthEndpoints
{
    public static IEndpointRouteBuilder MapHealthEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("health", (StudioHealth health, CancellationToken cancellationToken) =>
            health.ReportAsync(cancellationToken));

        return api;
    }
}
