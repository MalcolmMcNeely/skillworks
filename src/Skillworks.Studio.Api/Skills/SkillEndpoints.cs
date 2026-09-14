using Skillworks.Core.Filters;
using Skillworks.Core.Skills;

namespace Skillworks.Studio.Api.Skills;

public static class SkillEndpoints
{
    public static IEndpointRouteBuilder MapSkillEndpoints(this IEndpointRouteBuilder api)
    {
        // The filter binds as one object, not four parameters, so every telemetry list narrows the same way.
        api.MapGet("skills", ([AsParameters] TelemetryFilter filter, SkillReport report, CancellationToken cancellationToken) =>
            report.SkillsAsync(filter, cancellationToken));

        return api;
    }
}
