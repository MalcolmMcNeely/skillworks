namespace Skillworks.Studio.Api.Tests.Skills;

public sealed record SkillsAnswer
{
    public required SkillRow[] Skills { get; init; }

    public required TurnTotalsRow? UnnamedSpend { get; init; }

    public required GapRow Gap { get; init; }

    public required SpanRow Span { get; init; }
}
