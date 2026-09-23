using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Filters;

namespace Skillworks.Core.Dashboard.Skills;

// Plugin skills come before any day, as a skill that never fires is named on no day.
public sealed record SkillsHead(DaySpan Span, IReadOnlyList<DateOnly> Days, IReadOnlyList<string> PluginSkills)
    : ArrivingLine("head");
