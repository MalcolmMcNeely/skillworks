using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;
using Skillworks.Core.Spend;

namespace Skillworks.Core.Skills;

public sealed record SkillTable(
    IReadOnlyList<SkillSummary> Skills,
    SkillSpend? UnnamedSpend,
    ProvenanceNote Provenance,
    DaySpan Span);
