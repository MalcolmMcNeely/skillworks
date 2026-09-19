using Skillworks.Core.Filters;
using Skillworks.Core.Sessions;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Studio.Api.Shared.Arriving;

namespace Skillworks.Studio.Api.Sessions;

public static class SessionEndpoints
{
    public static IEndpointRouteBuilder MapSessionEndpoints(this IEndpointRouteBuilder api)
    {
        // The filter binds as one object, not four parameters, so every list narrows the same way.
        api.MapGet(
            "sessions",
            ([AsParameters] Filter filter,
                [AsParameters] SessionOrder order,
                SessionReport report,
                CancellationToken cancellationToken) =>
                new ArrivingAnswer(report.AnswerAsync(filter, order, cancellationToken)));

        // The span narrows the read, so opening a run from a table narrowed to a day reads that day alone.
        api.MapGet(
            "sessions/{id}",
            (string id,
                [AsParameters] Filter filter,
                StepReport steps,
                CancellationToken cancellationToken) =>
                new ArrivingAnswer(steps.AnswerAsync(id, filter, cancellationToken)));

        return api;
    }
}
