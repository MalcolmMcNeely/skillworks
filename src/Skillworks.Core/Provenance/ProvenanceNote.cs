using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Provenance;

public sealed record ProvenanceNote(ProvenanceGap Gap, string? Missing, DateTimeOffset SinceUtc)
{
    internal static ProvenanceNote Of(
        string? unreachable,
        long events,
        bool truncated,
        bool? emitting,
        DateTimeOffset sinceUtc)
    {
        var (gap, missing) = (unreachable, events, truncated, emitting) switch
        {
            ({ } reason, _, _, _) => (
                ProvenanceGap.Unreachable,
                $"Studio could not read the events store: {reason}. Nothing it reads from there can be " +
                "shown until it can."),

            // Ahead of the switch: a cut answer is about what is on screen now, a switch off about what never arrives.
            (_, _, true, _) => (
                ProvenanceGap.Truncated,
                $"This period holds more events than Studio reads at once, so only the newest " +
                $"{events} of them are counted here. Narrow the dates to see the rest."),

            // Asked of the switch, not guessed: "nobody turned it on" is a fix for the developer, "nothing happened" is not.
            (_, 0, _, false) => (
                ProvenanceGap.TelemetryOff,
                "Claude Code is not emitting telemetry, so where these skills came from was never " +
                $"recorded. {TelemetrySwitch.TurnOnNote}"),

            // Said even for a full answer, because nothing has reached the events store since the switch went off.
            (_, _, _, false) => (
                ProvenanceGap.TelemetryOff,
                "Claude Code is not emitting telemetry, so nothing has reached the events store since " +
                $"the switch was turned off. What is here was recorded before then. {TelemetrySwitch.TurnOnNote}"),

            // Unreadable settings count as not emitting only for writing; on a screen Studio does not know, and says so.
            (_, 0, _, null) => (
                ProvenanceGap.TelemetryUnknown,
                "The events store holds nothing for this period, and Studio cannot read Claude Code's " +
                "settings, so it cannot say whether telemetry was ever switched on. The Studio panel " +
                "names the file and what is wrong with it."),

            (_, 0, _, _) => (
                ProvenanceGap.Quiet,
                "Telemetry is on and the events store holds nothing for this period, so where these " +
                "skills came from is not known. Anything from before the switch was flipped was never recorded."),

            _ => (ProvenanceGap.Complete, (string?)null),
        };

        return new ProvenanceNote(gap, missing, sinceUtc);
    }
}
