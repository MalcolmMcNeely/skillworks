namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed record SkillCallRow
{
    public required string Id { get; init; }

    public required string Skill { get; init; }

    public required DateTimeOffset AtUtc { get; init; }

    public required long FollowedMs { get; init; }

    public required string? Trigger { get; init; }
}
