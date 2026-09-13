using Skillworks.Core.Settings;

namespace Skillworks.Core.Provenance;

/// <summary>
/// One way a skill was delivered and set off, as the events store recorded it. Two skills that
/// share a name are told apart by this and by nothing else a transcript holds.
/// </summary>
public sealed record SkillOrigin(string? Trigger, string? Source, string? Plugin, string? Marketplace);

/// <summary>
/// Why provenance is not here, when it is not. Every one of these comes back as an empty list of
/// events, so a caller that only counted rows could not tell an outage from a quiet afternoon.
/// </summary>
public enum ProvenanceGap
{
    /// <summary>Nothing fell short. Every skill on screen carries whatever the store recorded for it.</summary>
    Complete,

    /// <summary>Studio could not read the events store at all, so nothing can be said either way.</summary>
    Unreachable,

    /// <summary>The period holds more events than one read takes, so only the newest are counted.</summary>
    Truncated,

    /// <summary>Claude Code is not emitting, so nothing has reached the store since it was turned off.</summary>
    TelemetryOff,

    /// <summary>Studio cannot read Claude Code's settings, so it cannot say whether telemetry is on.</summary>
    TelemetryUnknown,

    /// <summary>The store answered and holds nothing, and Claude Code is emitting. Nothing fired.</summary>
    Quiet,
}

/// <summary>What the events store had to say about the period being looked at.</summary>
/// <param name="Gap">Which of the ways provenance can be absent this answer is, if any.</param>
/// <param name="Missing">
/// The same thing in words, or null when nothing is missing. A screen shows this beside the answer,
/// because a gap that reads as a fact is the one failure this half cannot afford.
/// </param>
/// <param name="SinceUtc">The earliest moment the answer covers, which a question about all time needs.</param>
public sealed record ProvenanceNote(ProvenanceGap Gap, string? Missing, DateTimeOffset SinceUtc);

/// <summary>
/// One read of the events store, ready to be joined to what the transcripts hold. It answers by
/// skill name for a table and by name and moment for a single firing, which ADR 0002 records as
/// the price of keeping the two stores apart.
/// </summary>
public sealed class ProvenanceReading
{
    /// <summary>
    /// How near an event has to be to a firing to be the same one. A skill that fired twice in a
    /// session is minutes apart, and a join on the name alone would hand one firing the other's
    /// trigger.
    /// </summary>
    internal static readonly TimeSpan Tolerance = TimeSpan.FromMinutes(2);

    private readonly IReadOnlyDictionary<string, IReadOnlyList<SkillEvent>> _bySkill;

    /// <param name="emitting">
    /// Whether Claude Code is filling the store right now, or null when Studio could not read the
    /// settings and so cannot say. It is the only thing that tells a period with no provenance from
    /// a period that was never recorded in the first place.
    /// </param>
    internal ProvenanceReading(EventReading reading, DateTimeOffset sinceUtc, bool? emitting)
    {
        _bySkill = reading.Events
            .GroupBy(recorded => recorded.Skill)
            .ToDictionary(group => group.Key, IReadOnlyList<SkillEvent> (group) => [.. group]);

        var (gap, missing) = Why(reading, emitting);

        Note = new ProvenanceNote(gap, missing, sinceUtc);
    }

    public ProvenanceNote Note { get; }

    /// <summary>
    /// Every way one skill name was delivered inside the period, without repeats. Empty means the
    /// store recorded nothing for the name, which <see cref="Note"/> explains.
    /// </summary>
    public IReadOnlyList<SkillOrigin> Of(string skill) =>
    [
        .. Events(skill)
            .Select(Origin)
            .Distinct()
            .OrderBy(origin => origin.Marketplace, StringComparer.OrdinalIgnoreCase)
            .ThenBy(origin => origin.Plugin, StringComparer.OrdinalIgnoreCase)
            .ThenBy(origin => origin.Trigger, StringComparer.OrdinalIgnoreCase)
    ];

    /// <summary>
    /// Where one firing came from: the nearest event of the same name, and nothing at all when the
    /// nearest is too far away to be it.
    /// </summary>
    public SkillOrigin? Nearest(string skill, DateTimeOffset at)
    {
        var nearest = Events(skill)
            .Where(recorded => Apart(recorded, at) <= Tolerance)
            .OrderBy(recorded => Apart(recorded, at))
            .FirstOrDefault();

        return nearest is null ? null : Origin(nearest);
    }

    /// <summary>
    /// What is not here. An outage, a switch that was never flipped, a quiet period and a period too
    /// big to read in one go are all gaps in the answer, and each says which it is rather than
    /// leaving a column to be read as a fact.
    /// </summary>
    private static (ProvenanceGap Gap, string? Missing) Why(EventReading reading, bool? emitting) => reading switch
    {
        { Unreachable: { } reason } => (
            ProvenanceGap.Unreachable,
            $"Studio could not read the events store, so it cannot say where a skill came from: " +
            $"{reason}. What each skill did and what it cost come from the transcripts and are unaffected."),

        // Ahead of the switch, because a cut answer is about what is on the screen now and a switch
        // that is off is about what will never arrive.
        { Truncated: true } => (
            ProvenanceGap.Truncated,
            $"This period holds more events than Studio reads at once, so only the newest " +
            $"{reading.Events.Count} of them are counted here. Narrow the dates to see the rest."),

        // Asked of the switch rather than guessed at. "Nobody turned it on" and "nothing happened"
        // are different problems with different answers, and only one of them a developer can fix.
        { Events.Count: 0 } when emitting is false => (
            ProvenanceGap.TelemetryOff,
            "Claude Code is not emitting telemetry, so where these skills came from was never " +
            $"recorded. {TelemetrySwitch.TurnOnNote}"),

        // Said even where the answer is full, because the period runs up to now and nothing has
        // reached the store since the switch went off.
        _ when emitting is false => (
            ProvenanceGap.TelemetryOff,
            "Claude Code is not emitting telemetry, so nothing has reached the events store since " +
            $"the switch was turned off. What is here was recorded before then. {TelemetrySwitch.TurnOnNote}"),

        // The switch reports settings it could not parse as not emitting, which is the safe answer
        // for writing them and would be a lie on a screen. Studio does not know, and says so.
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
