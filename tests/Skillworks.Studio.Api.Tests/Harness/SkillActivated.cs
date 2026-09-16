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

    internal static SkillActivated[] AtEveryMidnight(string skill, string firstDay, string lastDay)
    {
        var first = DateOnly.Parse(firstDay, CultureInfo.InvariantCulture);
        var last = DateOnly.Parse(lastDay, CultureInfo.InvariantCulture);

        return
        [
            .. Enumerable
                .Range(0, last.DayNumber - first.DayNumber + 1)
                .Select(day => new SkillActivated(skill, first.AddDays(day).ToString("yyyy-MM-dd'T00:00:00.000Z'", CultureInfo.InvariantCulture)))
        ];
    }
}
