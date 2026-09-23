using Skillworks.Core.Dashboard.Spend;
using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Dashboard.Skills;

// UnnarrowedEvents ignores the filter, so a filter that matches nothing on a busy day is not called quiet.
public sealed record SkillsDay(
    DateOnly Day,
    IReadOnlyList<SkillSummary> Skills,
    TurnTotals? UnnamedSpend,
    long UnnarrowedEvents)
    : ArrivingLine("day");
