using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Gaps;

public sealed record Gap(GapKind Kind, string? Missing)
{
    internal static Gap Of(string? unreachable, long events, bool? emitting)
    {
        var (kind, missing) = (unreachable, events, emitting) switch
        {
            ({ } reason, _, _) => (
                GapKind.Unreachable,
                $"Studio could not read the events store: {reason}. Nothing it reads from there can be " +
                "shown until it can."),

            // Asked of the switch, not guessed: "nobody turned it on" is a fix for the developer, "nothing happened" is not.
            (_, 0, false) => (
                GapKind.TelemetryOff,
                "Claude Code is not emitting telemetry, so where these skills came from was never " +
                $"recorded. {TelemetrySwitch.TurnOnNote}"),

            // Said even for a full answer, because nothing has reached the events store since the switch went off.
            (_, _, false) => (
                GapKind.TelemetryOff,
                "Claude Code is not emitting telemetry, so nothing has reached the events store since " +
                $"the switch was turned off. What is here was recorded before then. {TelemetrySwitch.TurnOnNote}"),

            // Unreadable settings count as not emitting only for writing; on a screen Studio does not know, and says so.
            (_, 0, null) => (
                GapKind.TelemetryUnknown,
                "The events store holds nothing for this period, and Studio cannot read Claude Code's " +
                "settings, so it cannot say whether telemetry was ever switched on. The Studio panel " +
                "names the file and what is wrong with it."),

            (_, 0, _) => (
                GapKind.Quiet,
                "Telemetry is on and the events store holds nothing for this period, so where these " +
                "skills came from is not known. Anything from before the switch was flipped was never recorded."),

            _ => (GapKind.Complete, (string?)null),
        };

        return new Gap(kind, missing);
    }
}
