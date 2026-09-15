using Skillworks.Core.Arriving;
using Skillworks.Core.Spend;

namespace Skillworks.Core.Skills;

// UnnarrowedEvents ignores the filter, so a filter that matches nothing on a busy day is not called quiet.
public sealed record SkillsDay(
    DateOnly Day,
    IReadOnlyList<SkillSummary> Skills,
    TurnTotals? UnnamedSpend,
    long UnnarrowedEvents)
    : ArrivingLine("day");
