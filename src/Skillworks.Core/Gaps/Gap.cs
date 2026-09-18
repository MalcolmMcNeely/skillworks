using System.Globalization;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Gaps;

public sealed record Gap(GapKind Kind, string? Missing)
{
    internal static Gap Of(string? unreachable, IReadOnlyList<DateOnly> unread, long events, bool? emitting)
    {
        var (kind, missing) = (unreachable, events, emitting) switch
        {
            // Only the unread days are short, as every day that landed is whole.
            ({ } reason, _, _) => (
                GapKind.Unreachable,
                $"Studio could not read the events store: {reason}. Nothing is shown for {Listed(unread)}."),

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
                "settings, so it cannot say whether telemetry was ever switched on. The Telemetry switch " +
                "names the file and what is wrong with it."),

            (_, 0, _) => (
                GapKind.Quiet,
                "Telemetry is on and the events store holds nothing for this period, so where these " +
                "skills came from is not known. Anything from before the switch was flipped was never recorded."),

            _ => (GapKind.Complete, (string?)null),
        };

        return new Gap(kind, missing);
    }

    // The switch is asked for the next action alone, which is the one part of this that differs by machine.
    internal static Gap OfWords(bool? on) =>
        new(
            GapKind.WordsOff,
            "Claude Code withheld the words of this run's prompts, so it cannot be read in full. " +
            on switch
            {
                false => TelemetrySwitch.TurnOnNote,

                true => "The Telemetry switch records them on this machine, so a run started since it was " +
                        "turned on carries its words. This one cannot be raised.",

                // A guess of on would promise the next run reads in full, from a file Studio never read.
                _ => "Studio cannot read Claude Code's settings, so it cannot say whether the words are " +
                     "recorded here now. The Telemetry switch names the file and what is wrong with it.",
            });

    internal static Gap OfSpans(string? unreachable, int spans, bool? tracing)
    {
        var (kind, missing) = (unreachable, spans, tracing) switch
        {
            ({ } reason, _, _) => (
                GapKind.Unreachable,
                $"Studio could not read the trace store: {reason}. Which agent ran each step is not known."),

            // Said before the switch is asked, because spans that landed are the answer either way.
            (_, > 0, _) => (GapKind.Complete, (string?)null),

            (_, _, false) => (
                GapKind.TelemetryOff,
                "Claude Code is not sending traces, so which agent ran each step was never recorded. " +
                TelemetrySwitch.TurnOnNote),

            (_, _, null) => (
                GapKind.TelemetryUnknown,
                "The trace store holds nothing for this run, and Studio cannot read Claude Code's settings, " +
                "so it cannot say whether traces were ever switched on. The Telemetry switch names the file " +
                "and what is wrong with it."),

            _ => (
                GapKind.Quiet,
                "Traces are on and the trace store holds nothing for this run, so which agent ran each step " +
                "is not known. Anything from before the switch was flipped was never recorded."),
        };

        return new Gap(kind, missing);
    }

    // A store that holds nothing is a true answer, as a run it says nothing about is Thin.
    internal static Gap OfDepths(string? unreachable) =>
        unreachable is { } reason
            ? new Gap(
                GapKind.Unreachable,
                $"Studio could not read the trace store: {reason}. Which runs can be read in full is not known.")
            : new Gap(GapKind.Complete, null);

    private static string Listed(IReadOnlyList<DateOnly> days)
    {
        string[] names = [.. days.Select(day => day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture))];

        return names.Length > 1 ? $"{string.Join(", ", names[..^1])} and {names[^1]}" : string.Concat(names);
    }
}
