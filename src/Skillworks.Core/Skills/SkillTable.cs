using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;
using Skillworks.Core.Spend;

namespace Skillworks.Core.Skills;

public sealed record SkillTable(
    IReadOnlyList<SkillSummary> Skills,
    TurnTotals? UnnamedSpend,
    Gap Gap,
    DaySpan Span);
