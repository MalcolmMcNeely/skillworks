using Skillworks.Core.Arriving;

namespace Skillworks.Core.Sessions.SkillCalls;

public sealed record SkillCallsPage(IReadOnlyList<SkillCall> SkillCalls) : ArrivingLine("skillCalls");
