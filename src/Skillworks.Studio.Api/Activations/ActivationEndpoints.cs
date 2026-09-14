using Skillworks.Core.Skills;
using Skillworks.Core.Telemetry;

namespace Skillworks.Studio.Api.Activations;

public static class ActivationEndpoints
{
    public static IEndpointRouteBuilder MapActivationEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("activations", ([AsParameters] TelemetryFilter filter, ActivationReport activations, CancellationToken cancellationToken) =>
            activations.ListAsync(filter, cancellationToken));

        // No filter: narrowing a firing opened by its id would answer the link with a blank page once the filter moved on.
        api.MapGet("activations/{id}", async (string id, ActivationReport activations, CancellationToken cancellationToken) =>
            await activations.OpenAsync(id, cancellationToken) is { } activation
                ? Results.Ok(activation)
                : Results.NotFound());

        return api;
    }
}
