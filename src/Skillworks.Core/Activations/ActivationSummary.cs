using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

public sealed record ActivationSummary(
    string Id,
    string Skill,
    string? Repository,
    string? Branch,
    string? Model,
    string? Effort,
    DateTimeOffset TimestampUtc)
{
    // Joined on afterwards: transcripts, which ActivationStore reads, do not record where a firing came from.
    public SkillOrigin? Origin { get; init; }
}
