using System.Globalization;
using Skillworks.Core.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Harness;

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

    public string Session { get; init; } = TestLoki.Session;

    public string? Person { get; init; } = TestLoki.Person;

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

    internal static SkillActivated[] AtEveryMidnight(string skill, DateOnly firstDay, DateOnly lastDay) =>
    [
        .. Enumerable
            .Range(0, lastDay.DayNumber - firstDay.DayNumber + 1)
            // Named in full, because this record's own At wins over the imported one.
            .Select(day => new SkillActivated(skill, Recently.At(firstDay.AddDays(day), "00:00:00.000")))
    ];
}
