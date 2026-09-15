using System.Globalization;

namespace Skillworks.Studio.Api.Tests.Harness;

// As sent with OTEL_LOG_TOOL_DETAILS=1, the setting that keeps a plugin skill's names.
public sealed record SkillActivated(
    string Skill,
    string At,
    string? Trigger = null,
    string? Source = null,
    string? Plugin = null,
    string? Marketplace = null,
    string? Owner = null,
    string? RepositoryName = null)
{
    internal const string EventName = "skill_activated";

    internal DateTimeOffset Moment => DateTimeOffset.Parse(At, CultureInfo.InvariantCulture);

    internal (string Key, string? Value)[] Attributes =>
    [
        ("skill.name", Skill),
        ("invocation_trigger", Trigger),
        ("skill.source", Source),
        ("plugin.name", Plugin),
        ("marketplace.name", Marketplace),
        ("vcs.owner.name", Owner),
        ("vcs.repository.name", RepositoryName),
    ];
}
