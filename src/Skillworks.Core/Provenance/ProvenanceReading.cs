using Skillworks.Core.EventsStore;
using Skillworks.Core.Telemetry;

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

        var (gap, missing) = Why(reading, emitting);

        Note = new ProvenanceNote(gap, missing, sinceUtc);
    }

    public ProvenanceNote Note { get; }

    public IReadOnlyList<SkillOrigin> Of(string skill) =>
    [
        .. Events(skill)
            .Select(Origin)
            .Distinct()
            .OrderBy(origin => origin.Marketplace, StringComparer.OrdinalIgnoreCase)
            .ThenBy(origin => origin.Plugin, StringComparer.OrdinalIgnoreCase)
            .ThenBy(origin => origin.Trigger, StringComparer.OrdinalIgnoreCase)
    ];

    public SkillOrigin? Nearest(string skill, DateTimeOffset at)
    {
        var nearest = Events(skill)
            .Where(recorded => Apart(recorded, at) <= Tolerance)
            .OrderBy(recorded => Apart(recorded, at))
            .FirstOrDefault();

        return nearest is null ? null : Origin(nearest);
    }

    private static (ProvenanceGap Gap, string? Missing) Why(EventReading reading, bool? emitting) => reading switch
    {
        { Unreachable: { } reason } => (
            ProvenanceGap.Unreachable,
            $"Studio could not read the events store, so it cannot say where a skill came from: " +
            $"{reason}. What each skill did and what it cost come from the transcripts and are unaffected."),

        // Ahead of the switch: a cut answer is about what is on screen now, a switch off about what never arrives.
        { Truncated: true } => (
            ProvenanceGap.Truncated,
            $"This period holds more events than Studio reads at once, so only the newest " +
            $"{reading.Events.Count} of them are counted here. Narrow the dates to see the rest."),

        // Asked of the switch, not guessed: "nobody turned it on" is a fix for the developer, "nothing happened" is not.
        { Events.Count: 0 } when emitting is false => (
            ProvenanceGap.TelemetryOff,
            "Claude Code is not emitting telemetry, so where these skills came from was never " +
            $"recorded. {TelemetrySwitch.TurnOnNote}"),

        // Said even for a full answer, because nothing has reached the events store since the switch went off.
        _ when emitting is false => (
            ProvenanceGap.TelemetryOff,
            "Claude Code is not emitting telemetry, so nothing has reached the events store since " +
            $"the switch was turned off. What is here was recorded before then. {TelemetrySwitch.TurnOnNote}"),

        // Unreadable settings count as not emitting only for writing; on a screen Studio does not know, and says so.
        { Events.Count: 0 } when emitting is null => (
            ProvenanceGap.TelemetryUnknown,
            "The events store holds nothing for this period, and Studio cannot read Claude Code's " +
            "settings, so it cannot say whether telemetry was ever switched on. The Studio panel " +
            "names the file and what is wrong with it."),

        { Events.Count: 0 } => (
            ProvenanceGap.Quiet,
            "Telemetry is on and the events store holds nothing for this period, so where these " +
            "skills came from is not known. Anything from before the switch was flipped was never recorded."),

        _ => (ProvenanceGap.Complete, null),
    };

    private static SkillOrigin Origin(SkillEvent recorded) =>
        new(recorded.Trigger, recorded.Source, recorded.Plugin, recorded.Marketplace);

    private static TimeSpan Apart(SkillEvent recorded, DateTimeOffset at) => (recorded.At - at).Duration();

    private IReadOnlyList<SkillEvent> Events(string skill) => _bySkill.GetValueOrDefault(skill, []);
}
