using Skillworks.Core.Shared.Health;

namespace Skillworks.Studio.Api.Shared.Health;

public static class HealthEndpoints
{
    public static IEndpointRouteBuilder MapHealthEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("health", (StudioHealth health, CancellationToken cancellationToken) =>
            health.ReportAsync(cancellationToken));

        return api;
    }
}
