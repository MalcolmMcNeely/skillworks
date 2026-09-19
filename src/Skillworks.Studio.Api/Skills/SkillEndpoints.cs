using Skillworks.Core.Filters;
using Skillworks.Core.Skills;
using Skillworks.Studio.Api.Shared.Arriving;

namespace Skillworks.Studio.Api.Skills;

public static class SkillEndpoints
{
    public static IEndpointRouteBuilder MapSkillEndpoints(this IEndpointRouteBuilder api)
    {
        // The filter binds as one object, not four parameters, so every list narrows the same way.
        api.MapGet("skills", ([AsParameters] Filter filter, SkillReport report, CancellationToken cancellationToken) =>
            new ArrivingAnswer(report.AnswerAsync(filter, cancellationToken)));

        return api;
    }
}
