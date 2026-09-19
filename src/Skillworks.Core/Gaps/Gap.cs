using System.Globalization;
using Skillworks.Core.Shared.Telemetry;

namespace Skillworks.Core.Gaps;

public sealed record Gap(GapKind Kind, string? Missing)
{
    internal static Gap Of(string? unreachable, IReadOnlyList<DateOnly> unread, long events, bool? emitting)
    {
        var (kind, missing) = (unreachable, events, emitting) switch
        {
            // Only the unread days are short, as every day that landed is whole.
            ({ } reason, _, _) => (GapKind.Unreachable, Unread(reason, Listed(unread))),

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

    // One Gap rides the end line and two stores can fall short at once, so both sentences ride it
    // together rather than the second one going unsaid.
    internal static Gap Beside(Gap first, Gap second) => new(first.Kind, $"{first.Missing} {second.Missing}");

    // The rows stand without them, so this names the columns left empty rather than emptying the table.
    internal static Gap OfMeasures(string? unreachable, IReadOnlyList<string> measures) =>
        unreachable is null
            ? new Gap(GapKind.Complete, null)
            : new Gap(GapKind.Unreachable, Unread(unreachable, Listed(measures)));

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

    internal static Gap OfSpans(string? unreachable, bool shortened, int spans, bool? tracing)
    {
        var (kind, missing) = (unreachable, shortened, spans, tracing) switch
        {
            ({ } reason, _, _, _) => (
                GapKind.Unreachable,
                $"Studio could not read the trace store: {reason}. Which agent ran each step is not known."),

            // Ahead of the spans that did land, or a run the store cut in half would read as a whole one.
            (_, true, _, _) => (
                GapKind.Shortened,
                "The trace store held more traces for this run than one read takes, so what is shown is part " +
                "of it. Which agent ran a step it left out is not known."),

            // Said before the switch is asked, because spans that landed are the answer either way.
            (_, _, > 0, _) => (GapKind.Complete, (string?)null),

            (_, _, _, false) => (
                GapKind.TelemetryOff,
                "Claude Code is not sending traces, so which agent ran each step was never recorded. " +
                TelemetrySwitch.TurnOnNote),

            (_, _, _, null) => (
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
    internal static Gap OfDepths(string? unreachable, bool shortened)
    {
        var (kind, missing) = (unreachable, shortened) switch
        {
            ({ } reason, _) => (
                GapKind.Unreachable,
                $"Studio could not read the trace store: {reason}. Which runs can be read in full is not " +
                "known, so the table is not narrowed by it."),

            (_, true) => (
                GapKind.Shortened,
                "The trace store held more runs for this period than one read takes, so which runs can be " +
                "read in full is not known and the table is not narrowed by it. Ask for fewer days, so the " +
                "whole of the answer fits one read."),

            _ => (GapKind.Complete, (string?)null),
        };

        return new Gap(kind, missing);
    }

    private static string Unread(string reason, string missing) =>
        $"Studio could not read the events store: {reason}. Nothing is shown for {missing}.";

    private static string Listed(IReadOnlyList<DateOnly> days) =>
        Listed([.. days.Select(day => day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture))]);

    private static string Listed(IReadOnlyList<string> names) =>
        names.Count > 1
            ? $"{string.Join(", ", names.Take(names.Count - 1))} and {names[^1]}"
            : string.Concat(names);
}
