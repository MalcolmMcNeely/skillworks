using Skillworks.Core.Filters;
using Skillworks.Core.Sessions;
using Skillworks.Studio.Api.Arriving;

namespace Skillworks.Studio.Api.Sessions;

public static class SessionEndpoints
{
    public static IEndpointRouteBuilder MapSessionEndpoints(this IEndpointRouteBuilder api)
    {
        // The filter binds as one object, not four parameters, so every list narrows the same way.
        api.MapGet("sessions", ([AsParameters] Filter filter, SessionReport report, CancellationToken cancellationToken) =>
            new ArrivingAnswer(report.AnswerAsync(filter, cancellationToken)));

        return api;
    }
}
