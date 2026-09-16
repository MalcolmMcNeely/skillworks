using Skillworks.Core.EventsStore;
using Skillworks.Core.Provenance;
using Skillworks.Core.Sessions.SkillCalls;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private const string FiringEvent = "skill_activated";

    private static IReadOnlyList<SkillCall> Fired(IReadOnlyList<EventLine> lines)
    {
        var lastEvent = lines[^1].At;

        var fired =
            (from place in Enumerable.Range(0, lines.Count)
                let line = lines[place]
                where Named(FiringEvent)(line)
                let skill = line.Attribute(EventAttributes.Skill)
                where skill is { Length: > 0 }
                select (Line: line, Id: Identity(line, place), Skill: skill))
            .ToList();

        return
        [
            .. fired.Select((call, order) => new SkillCall(
                call.Id,
                call.Skill,
                call.Line.At,
                (long)((order + 1 < fired.Count ? fired[order + 1].Line.At : lastEvent) - call.Line.At).TotalMilliseconds,
                SkillOrigin.Of(call.Line.Attribute).Trigger))
        ];
    }
}
