namespace Skillworks.Core.Provenance;

/// <summary>
/// One way a skill was delivered and set off, as the events store recorded it. Two skills that
/// share a name are told apart by this and by nothing else a transcript holds.
/// </summary>
public sealed record SkillOrigin(string? Trigger, string? Source, string? Plugin, string? Marketplace);

/// <summary>What the events store had to say about the period being looked at.</summary>
/// <param name="Reachable">False when Studio could not read the store at all.</param>
/// <param name="Missing">
/// What provenance is not here, or null when none is. A screen shows this beside the answer,
/// because a gap that reads as a fact is the one failure this half cannot afford.
/// </param>
/// <param name="SinceUtc">The earliest moment the answer covers, which a question about all time needs.</param>
public sealed record ProvenanceNote(bool Reachable, string? Missing, DateTimeOffset SinceUtc);

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

    internal ProvenanceReading(EventReading reading, DateTimeOffset sinceUtc)
    {
        _bySkill = reading.Events
            .GroupBy(recorded => recorded.Skill)
            .ToDictionary(group => group.Key, IReadOnlyList<SkillEvent> (group) => [.. group]);

        Note = new ProvenanceNote(reading.Unreachable is null, Why(reading), sinceUtc);
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
    /// What is not here. An outage, a quiet period and a period too big to read in one go are all
    /// gaps in the answer, and each says which it is rather than leaving a column to be read as a
    /// fact.
    /// </summary>
    private static string? Why(EventReading reading) => reading switch
    {
        { Unreachable: { } reason } =>
            $"Studio could not read the events store, so it cannot say where a skill came from: {reason}.",
        { Events.Count: 0 } =>
            "The events store has nothing for this period, so where these skills came from is not " +
            "known. Telemetry may have been switched off at the time.",
        { Truncated: true } =>
            $"This period holds more events than Studio reads at once, so only the newest " +
            $"{reading.Events.Count} of them are counted here. Narrow the dates to see the rest.",
        _ => null,
    };

    private static SkillOrigin Origin(SkillEvent recorded) =>
        new(recorded.Trigger, recorded.Source, recorded.Plugin, recorded.Marketplace);

    private static TimeSpan Apart(SkillEvent recorded, DateTimeOffset at) => (recorded.At - at).Duration();

    private IReadOnlyList<SkillEvent> Events(string skill) => _bySkill.GetValueOrDefault(skill, []);
}
