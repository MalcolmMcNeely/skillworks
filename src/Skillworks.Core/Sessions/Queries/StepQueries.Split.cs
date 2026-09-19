using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Split;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    // An older Claude Code names no source on a Turn, and a Turn that names none is the main agent's.
    private const string MainAgent = "main";

    public static SplitPage Split(OpenedRun opened, OpenedSpans traced, IReadOnlyList<Subagent> ran)
    {
        if (opened.Run is null)
        {
            return new SplitPage(traced.Traced, [], []);
        }

        var worked = Worked(opened, traced, ran);

        return new SplitPage(traced.Traced, Apart([.. worked, .. Idle(opened, worked)]), worked);
    }

    private static IReadOnlyList<PartSpell> Worked(
        OpenedRun opened,
        OpenedSpans traced,
        IReadOnlyList<Subagent> ran)
    {
        var keys = opened.Keys.ToDictionary(key => key.Step, key => key.Key, StringComparer.Ordinal);

        // A call in here has a Subagent's spell covering it, so a Thin run counts the call rather than losing it.
        var started = traced.Wrapped.Values.Select(root => root.ToolUse).ToHashSet(StringComparer.Ordinal);
        var worked = new List<PartSpell>();

        foreach (var (line, step) in opened.Drawn)
        {
            // A Subagent's spell below covers its Steps, so counting one here would count it twice.
            var ownWork = !traced.Agents.ContainsKey(step.Id);
            var key = keys.GetValueOrDefault(step.Id);

            switch (step.Kind)
            {
                case StepKind.Turn when ownWork:
                    worked.Add(new PartSpell(Aside(line) ? SplitPart.Side : SplitPart.Model, step.AtUtc, step.LengthMs));

                    break;

                case StepKind.Tool when ownWork && (key is null || !started.Contains(key)):
                    worked.Add(Used(step, key is null ? null : traced.Waited.GetValueOrDefault(key)));

                    break;

                // Claude Code puts no length on a refusal, so this counts only where one was recorded.
                case StepKind.Refused:
                    worked.Add(new PartSpell(SplitPart.Waiting, step.AtUtc, step.LengthMs));

                    break;
            }
        }

        worked.AddRange(traced.Waited.Values.Select(wait => Spelled(SplitPart.Waiting, wait)));
        worked.AddRange(traced.Hooked.Select(hook => Spelled(SplitPart.Hooks, hook)));
        worked.AddRange(ran.Select(agent => new PartSpell(SplitPart.Subagents, agent.AtUtc, agent.LengthMs)));

        return worked;
    }

    // The wait for a person sits at the head of the call, so what is left of it is the tool's own work.
    private static PartSpell Used(Step step, Spell? waited)
    {
        var ended = Ends(step.AtUtc, step.LengthMs);

        if (waited is null)
        {
            return new PartSpell(SplitPart.Tools, step.AtUtc, step.LengthMs);
        }

        var allowed = Ends(waited.AtUtc, waited.LengthMs);
        var ran = allowed < step.AtUtc ? step.AtUtc : allowed > ended ? ended : allowed;

        return new PartSpell(SplitPart.Tools, ran, (long)(ended - ran).TotalMilliseconds);
    }

    private static PartSpell Spelled(SplitPart part, Spell spell) => new(part, spell.AtUtc, spell.LengthMs);

    private static bool Aside(EventLine line) =>
        line.Attribute(EventAttributes.QuerySource) is { Length: > 0 } source && source != MainAgent;

    private static IReadOnlyList<PartSpell> Idle(OpenedRun opened, IReadOnlyList<PartSpell> worked)
    {
        var run = opened.Run!;
        var quiet = opened.Said.Select(said => new PartSpell(SplitPart.Quiet, said.AtUtc, said.LengthMs)).ToList();

        // A Turn's start is worked back from its length, so a Step can begin before the run's first event.
        var from = worked.Concat(quiet).Select(spell => spell.AtUtc).Append(run.StartedUtc).Min();
        var to = worked.Concat(quiet).Select(spell => Ends(spell.AtUtc, spell.LengthMs))
            .Append(Ends(run.StartedUtc, run.LengthMs))
            .Max();

        return [.. quiet, new PartSpell(SplitPart.YourTurn, from, (long)(to - from).TotalMilliseconds)];
    }

    private static IReadOnlyList<PartSpell> Apart(IReadOnlyList<PartSpell> spells)
    {
        var starting = spells.Where(spell => spell.LengthMs > 0).OrderBy(spell => spell.AtUtc).ToList();

        var edges = starting
            .SelectMany(spell => new[] { spell.AtUtc, Ends(spell.AtUtc, spell.LengthMs) })
            .Distinct()
            .Order()
            .ToList();

        var open = new List<PartSpell>();
        var apart = new List<PartSpell>();
        var next = 0;

        for (var edge = 0; edge + 1 < edges.Count; edge++)
        {
            var from = edges[edge];

            while (next < starting.Count && starting[next].AtUtc <= from)
            {
                open.Add(starting[next++]);
            }

            open.RemoveAll(spell => Ends(spell.AtUtc, spell.LengthMs) <= from);

            if (open.Count > 0)
            {
                Took(apart, open.Min(spell => spell.Part), from, edges[edge + 1]);
            }
        }

        return apart;
    }

    // Slices of one part that touch are one spell, or a run would come back with a spell for every edge in it.
    private static void Took(List<PartSpell> apart, SplitPart part, DateTimeOffset from, DateTimeOffset to)
    {
        if (apart.Count > 0 &&
            apart[^1].Part == part &&
            Ends(apart[^1].AtUtc, apart[^1].LengthMs) == from)
        {
            apart[^1] = apart[^1] with { LengthMs = (long)(to - apart[^1].AtUtc).TotalMilliseconds };

            return;
        }

        apart.Add(new PartSpell(part, from, (long)(to - from).TotalMilliseconds));
    }

    private static DateTimeOffset Ends(DateTimeOffset at, long lengthMs) => at.AddMilliseconds(lengthMs);
}
