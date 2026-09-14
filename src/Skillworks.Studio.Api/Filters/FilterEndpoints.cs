using Skillworks.Core.Skills;

namespace Skillworks.Studio.Api.Filters;

public static class FilterEndpoints
{
    public static IEndpointRouteBuilder MapFilterEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("filters", (SkillReport report, CancellationToken cancellationToken) =>
            report.ChoicesAsync(cancellationToken));

        return api;
    }
}
