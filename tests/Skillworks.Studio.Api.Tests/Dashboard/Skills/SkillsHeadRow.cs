using Skillworks.Studio.Api.Tests.Shared.Filters;

namespace Skillworks.Studio.Api.Tests.Dashboard.Skills;

public sealed record SkillsHeadRow
{
    public required SpanRow Span { get; init; }

    public required DateOnly[] Days { get; init; }

    public required string[] CatalogueSkills { get; init; }
}
