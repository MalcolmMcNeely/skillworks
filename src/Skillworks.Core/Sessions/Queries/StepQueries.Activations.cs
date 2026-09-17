using Skillworks.Core.EventsStore;
using Skillworks.Core.Provenance;
using Skillworks.Core.Sessions.Activations;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private const string ActivationEvent = "skill_activated";

    private static IReadOnlyList<Activation> Fired(IReadOnlyList<EventLine> lines)
    {
        var lastEvent = lines[^1].At;

        var fired =
            (from place in Enumerable.Range(0, lines.Count)
                let line = lines[place]
                where Named(ActivationEvent)(line)
                let skill = line.Attribute(EventAttributes.Skill)
                where skill is { Length: > 0 }
                select (Line: line, Id: Identity(line, place), Skill: skill))
            .ToList();

        return
        [
            .. fired.Select((activation, order) => new Activation(
                activation.Id,
                activation.Skill,
                activation.Line.At,
                (long)((order + 1 < fired.Count ? fired[order + 1].Line.At : lastEvent) - activation.Line.At).TotalMilliseconds,
                SkillOrigin.Of(activation.Line.Attribute).Trigger))
        ];
    }
}
