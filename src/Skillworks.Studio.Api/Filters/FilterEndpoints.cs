using Skillworks.Core.Filters;
using Skillworks.Core.Skills;
using Skillworks.Studio.Api.Shared.Arriving;

namespace Skillworks.Studio.Api.Filters;

public static class FilterEndpoints
{
    public static IEndpointRouteBuilder MapFilterEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("filters", ([AsParameters] Filter filter, SkillReport report, CancellationToken cancellationToken) =>
            new ArrivingAnswer(report.ChoicesAsync(filter, cancellationToken)));

        return api;
    }
}
