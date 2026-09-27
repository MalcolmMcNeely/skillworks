using Skillworks.Core.Sessions.Activations;
using Skillworks.Core.Shared.Provenance;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private const string ActivationEvent = "skill_activated";

    private static IReadOnlyList<Activation> Activated(IReadOnlyList<EventLine> lines)
    {
        var lastEvent = lines[^1].At;

        var activated =
            (from place in Enumerable.Range(0, lines.Count)
                let line = lines[place]
                where Named(ActivationEvent)(line)
                let skill = line.Attribute(EventAttributes.Skill)
                where skill is { Length: > 0 }
                select (Line: line, Id: Identity(line, place), Skill: skill))
            .ToList();

        return
        [
            .. activated.Select((activation, order) => new Activation(
                activation.Id,
                activation.Skill,
                activation.Line.At,
                (long)((order + 1 < activated.Count ? activated[order + 1].Line.At : lastEvent) - activation.Line.At).TotalMilliseconds,
                SkillOrigin.Of(activation.Line.Attribute).Trigger))
        ];
    }
}
