namespace Skillworks.Studio.Api.Tests.Skills;

public sealed record SkillsDayRow
{
    public required DateOnly Day { get; init; }

    public required SkillRow[] Skills { get; init; }

    public required TurnTotalsRow? UnnamedSpend { get; init; }

    public required long UnnarrowedEvents { get; init; }
}
