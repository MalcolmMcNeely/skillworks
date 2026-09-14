using Skillworks.Core.Provenance;

namespace Skillworks.Core.Telemetry;

public sealed record ActivationDetail(
    string Id,
    string Skill,
    string SessionId,
    string? Repository,
    string? Branch,
    string? Model,
    string? Effort,
    DateTimeOffset TimestampUtc,
    IReadOnlyList<ActivationArgument> Arguments)
{
    public SkillOrigin? Origin { get; init; }
}
