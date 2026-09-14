namespace Skillworks.Studio.Api.Tests.Skills;

public sealed record SkillsAnswer
{
    public required SkillRow[] Skills { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}
