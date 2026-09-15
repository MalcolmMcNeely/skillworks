using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Skills;

public sealed record SkillTable(IReadOnlyList<SkillSummary> Skills, ProvenanceNote Provenance, DaySpan Span);
