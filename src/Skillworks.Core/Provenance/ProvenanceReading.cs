using Skillworks.Core.EventsStore;

namespace Skillworks.Core.Provenance;

public sealed class ProvenanceReading
{
    // Tight: two firings of one skill in a session can be minutes apart and must not swap triggers.
    internal static readonly TimeSpan Tolerance = TimeSpan.FromMinutes(2);

    private readonly IReadOnlyDictionary<string, IReadOnlyList<SkillEvent>> _bySkill;

    internal ProvenanceReading(EventReading reading, DateTimeOffset sinceUtc, bool? emitting)
    {
        _bySkill = reading.Events
            .Select(SkillEvent.From)
            .OfType<SkillEvent>()
            .GroupBy(recorded => recorded.Skill)
            .ToDictionary(group => group.Key, IReadOnlyList<SkillEvent> (group) => [.. group]);

        Note = ProvenanceNote.Of(reading.Unreachable, reading.Events.Count, reading.Truncated, emitting, sinceUtc);
    }

    public ProvenanceNote Note { get; }

    public IReadOnlyList<SkillOrigin> Of(string skill) => SkillOrigin.Ordered(Events(skill).Select(recorded => recorded.Origin));

    public SkillOrigin? Nearest(string skill, DateTimeOffset at)
    {
        var nearest = Events(skill)
            .Where(recorded => Apart(recorded, at) <= Tolerance)
            .OrderBy(recorded => Apart(recorded, at))
            .FirstOrDefault();

        return nearest?.Origin;
    }

    private static TimeSpan Apart(SkillEvent recorded, DateTimeOffset at) => (recorded.At - at).Duration();

    private IReadOnlyList<SkillEvent> Events(string skill) => _bySkill.GetValueOrDefault(skill, []);
}
