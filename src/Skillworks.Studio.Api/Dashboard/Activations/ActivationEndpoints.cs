using Skillworks.Core.Dashboard.Activations;
using Skillworks.Core.Shared.Filters;
using Skillworks.Studio.Api.Shared.Arriving;

namespace Skillworks.Studio.Api.Dashboard.Activations;

public static class ActivationEndpoints
{
    public static IEndpointRouteBuilder MapActivationEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("activations", ([AsParameters] Filter filter, ActivationReport report, CancellationToken cancellationToken) =>
            new ArrivingAnswer(report.AnswerAsync(filter, cancellationToken)));

        return api;
    }
}
