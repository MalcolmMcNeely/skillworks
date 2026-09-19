using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Skills;

// Catalogue skills come before any day, as a skill that never fires is named on no day.
public sealed record SkillsHead(DaySpan Span, IReadOnlyList<DateOnly> Days, IReadOnlyList<string> CatalogueSkills)
    : ArrivingLine("head");
