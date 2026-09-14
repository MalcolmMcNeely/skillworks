namespace Skillworks.Studio.Api.Tests;

public sealed record SkillsAnswer
{
    public required SkillRow[] Skills { get; init; }

    public required ProvenanceRow Provenance { get; init; }
}
