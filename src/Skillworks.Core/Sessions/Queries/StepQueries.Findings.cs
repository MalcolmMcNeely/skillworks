using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Context;
using Skillworks.Core.Sessions.Findings;
using Skillworks.Core.Sessions.Split;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private const string RateLimitMarker = "ratelimit";

    // Only these write a file, so a run that reads one file twenty times crosses nothing.
    private static readonly string[] WritingTools = ["Edit", "Write", "NotebookEdit"];

    // Answered once off the events and again once the split has landed, so a slow Trace store never
    // leaves the list empty. Until the split is there, the three bars only a Span can measure read Not known.
    public static FindingsPage Found(OpenedRun opened, SplitPage? split = null, IReadOnlyList<Subagent>? ran = null)
    {
        if (opened.Run is not { } run)
        {
            return new FindingsPage([]);
        }

        var traces = split?.Traced == true;

        return new FindingsPage(
        [
            .. new[]
            {
                FailingAgain(opened.Drawn),
                EditedAgain(opened.Drawn),
                RateLimited(opened.Drawn),
                CacheRebuilt(opened.Sent),
                NearTheLimit(opened.Sent, opened.LimitTokens),
                Hooked(split, traces, run),
                Waiting(split, traces, run),
                Costly(ran ?? [], traces, run, opened.Called.Count),
            }.OfType<Finding>()
        ]);
    }

    private static Finding? FailingAgain(IReadOnlyList<DrawnStep> drawn)
    {
        // Only where the input was recorded, or two different commands would group as one command repeated.
        var worst = drawn
            .Where(each => each.Step.Kind == StepKind.Tool && each.Step.Fault)
            .Select(each => (each.Step, Input: Recorded(each.Line, EventAttributes.ToolInput)))
            .Where(each => each.Input is { Length: > 0 })
            .GroupBy(each => $"{each.Step.Tool}\n{each.Input}", StringComparer.Ordinal)
            .MaxBy(again => again.Count());

        if (worst is null)
        {
            return null;
        }

        var last = worst.Last();

        return Crossed(
            FindingKind.FailingAgain,
            worst.Count(),
            Bars.FailingAgain,
            ToolInput.ActedOn(last.Input) ?? last.Step.Tool,
            last.Step);
    }

    private static Finding? EditedAgain(IReadOnlyList<DrawnStep> drawn)
    {
        var worst = drawn
            .Where(each => each.Step.Kind == StepKind.Tool && each.Step.Tool is { } tool && WritingTools.Contains(tool))
            .Select(each => (each.Step, File: ToolInput.FileIn(Recorded(each.Line, EventAttributes.ToolInput))))
            .Where(each => each.File is { Length: > 0 })
            .GroupBy(each => each.File!, StringComparer.Ordinal)
            .MaxBy(again => again.Count());

        return worst is null
            ? null
            : Crossed(FindingKind.EditedAgain, worst.Count(), Bars.EditedAgain, worst.Key, worst.Last().Step);
    }

    // Claude Code names the kind of model error, and a rate limit is the one a person can act on.
    private static Finding? RateLimited(IReadOnlyList<DrawnStep> drawn)
    {
        var limited = drawn
            .Where(each => each.Step.Kind == StepKind.Fault && Limited(each.Step.Words))
            .Select(each => each.Step)
            .ToList();

        return limited.Count == 0
            ? null
            : Crossed(FindingKind.RateLimited, limited.Count, Bars.RateLimited, null, limited[^1]);
    }

    // Written as RateLimited and as rate_limit_error, and looking for "rate" alone would match generate.
    private static bool Limited(string? errorType) =>
        errorType?.Replace("_", "", StringComparison.Ordinal)
            .Replace("-", "", StringComparison.Ordinal)
            .Contains(RateLimitMarker, StringComparison.OrdinalIgnoreCase) == true;

    private static Finding? CacheRebuilt(IReadOnlyList<ContextPoint> sent)
    {
        var rebuilt = sent.Where(point => point.Rebuilt).ToList();

        return rebuilt.Count == 0
            ? null
            : Crossed(FindingKind.CacheRebuilt, rebuilt.Count, Bars.CacheRebuilt, null, rebuilt[^1]);
    }

    // No event states a window, so a run on a model that names none is never read as near a limit nobody knows.
    private static Finding? NearTheLimit(IReadOnlyList<ContextPoint> sent, long? limitTokens)
    {
        if (limitTokens is not { } limit || limit <= 0 || sent.Count == 0)
        {
            return null;
        }

        var fullest = sent.MaxBy(point => point.Tokens)!;

        return Crossed(FindingKind.NearTheLimit, (decimal)fullest.Tokens / limit, Bars.NearTheLimit, null, fullest);
    }

    private static Finding? Hooked(SplitPage? split, bool traces, Session run)
    {
        if (split is null || !traces)
        {
            return NotKnown(FindingKind.Hooks, Bars.Hooks, run);
        }

        var busy = Busy(split);

        return busy <= 0 || Longest(split, SplitPart.Hooks) is not { } longest
            ? null
            : Crossed(FindingKind.Hooks, Spent(split, SplitPart.Hooks) / (decimal)busy, Bars.Hooks, null, longest);
    }

    // Only a Span records the asking, so a run without them cannot tell a person's delay from the tool's own work.
    private static Finding? Waiting(SplitPage? split, bool traces, Session run)
    {
        if (split is null || !traces)
        {
            return NotKnown(FindingKind.Waiting, Bars.WaitingMs, run);
        }

        // The whole of the waiting is the figure, and the worst single wait is where a reader starts looking.
        return Longest(split, SplitPart.Waiting) is not { } longest
            ? null
            : Crossed(FindingKind.Waiting, Spent(split, SplitPart.Waiting), Bars.WaitingMs, null, longest);
    }

    private static Finding? Costly(IReadOnlyList<Subagent> ran, bool traces, Session run, int agentCalls)
    {
        // Fewer than two Agent calls in the events means there were never two siblings to compare, Span or no Span.
        if (!traces)
        {
            return agentCalls < 2 ? null : NotKnown(FindingKind.CostlySubagent, Bars.CostlySubagent, run);
        }

        if (ran.Count < 2)
        {
            return null;
        }

        // Against the middle of the others, so the runaway itself cannot raise the bar it is measured by.
        var byCost = ran.OrderBy(agent => agent.Cost).ToList();
        var dearest = byCost[^1];
        var middle = Middle([.. byCost[..^1].Select(agent => agent.Cost)]);

        return middle <= 0
            ? null
            : Crossed(
                FindingKind.CostlySubagent,
                dearest.Cost / middle,
                Bars.CostlySubagent,
                dearest.Name,
                new Spell(dearest.AtUtc, dearest.LengthMs));
    }

    private static decimal Middle(IReadOnlyList<decimal> sorted) =>
        sorted.Count % 2 == 1
            ? sorted[sorted.Count / 2]
            : (sorted[sorted.Count / 2 - 1] + sorted[sorted.Count / 2]) / 2;

    // Only the Parts something was running in, or an afternoon of waiting makes any hook look small.
    private static long Busy(SplitPage split) =>
        split.Parts
            .Where(spell => spell.Part is not (SplitPart.YourTurn or SplitPart.Quiet or SplitPart.Waiting))
            .Sum(spell => spell.LengthMs);

    private static long Spent(SplitPage split, SplitPart part) =>
        split.Parts.Where(spell => spell.Part == part).Sum(spell => spell.LengthMs);

    // A Finding made of many moments still points at one a reader can look at.
    private static Spell? Longest(SplitPage split, SplitPart part) =>
        split.Parts.Where(spell => spell.Part == part).MaxBy(spell => spell.LengthMs) is { } spell
            ? new Spell(spell.AtUtc, spell.LengthMs)
            : null;

    // The most recent time it happened, for every bar alike, so clicking one always lands in the same place.
    private static Finding? Crossed(FindingKind kind, decimal figure, decimal bar, string? subject, Step step) =>
        figure < bar ? null : new Finding(kind, subject, figure, bar, step.Id, step.AtUtc, step.LengthMs);

    private static Finding? Crossed(FindingKind kind, decimal figure, decimal bar, string? subject, ContextPoint point) =>
        figure < bar ? null : new Finding(kind, subject, figure, bar, point.Id, point.AtUtc, point.LengthMs);

    private static Finding? Crossed(FindingKind kind, decimal figure, decimal bar, string? subject, Spell spell) =>
        figure < bar ? null : new Finding(kind, subject, figure, bar, null, spell.AtUtc, spell.LengthMs);

    // Named with no figure, as leaving it out would read as a bar Studio measured and found clean.
    private static Finding NotKnown(FindingKind kind, decimal bar, Session run) =>
        new(kind, null, null, bar, null, run.StartedUtc, run.LengthMs);
}
