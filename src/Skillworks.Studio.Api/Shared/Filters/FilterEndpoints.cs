using Skillworks.Core.Shared.Filters;
using Skillworks.Studio.Api.Shared.Arriving;

namespace Skillworks.Studio.Api.Shared.Filters;

public static class FilterEndpoints
{
    public static IEndpointRouteBuilder MapFilterEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("filters", ([AsParameters] Filter filter, FilterChoices choices, CancellationToken cancellationToken) =>
            new ArrivingAnswer(choices.AnswerAsync(filter, cancellationToken)));

        return api;
    }
}
