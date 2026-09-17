using Skillworks.Core.EventsStore;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Split;
using Skillworks.Core.Sessions.Steps;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    // An older Claude Code names no source on a Turn, and a Turn that names none is the main agent's.
    private const string MainAgent = "main";

    public static SplitPage Split(OpenedRun opened, OpenedSpans traced, IReadOnlyList<Subagent> ran)
    {
        if (opened.Run is null)
        {
            return new SplitPage(traced.Depth, [], []);
        }

        var worked = Worked(opened, traced, ran);

        return new SplitPage(traced.Depth, Apart([.. worked, .. Idle(opened, worked)]), worked);
    }

    private static IReadOnlyList<Spell> Worked(
        OpenedRun opened,
        OpenedSpans traced,
        IReadOnlyList<Subagent> ran)
    {
        var keys = opened.Keys.ToDictionary(key => key.Step, key => key.Key, StringComparer.Ordinal);

        // Only a call a stint below stands for, so a Thin run counts the call rather than losing the time.
        var started = traced.Wrapped.Values.Select(root => root.ToolUse).ToHashSet(StringComparer.Ordinal);
        var worked = new List<Spell>();

        foreach (var (line, step) in opened.Drawn)
        {
            // A Subagent's stint below covers its Steps, so counting one here would count it twice.
            var ownWork = !traced.Agents.ContainsKey(step.Id);
            var key = keys.GetValueOrDefault(step.Id);

            switch (step.Kind)
            {
                case StepKind.Turn when ownWork:
                    worked.Add(new Spell(Aside(line) ? SplitPart.Side : SplitPart.Model, step.AtUtc, step.LengthMs));

                    break;

                case StepKind.Tool when ownWork && (key is null || !started.Contains(key)):
                    worked.Add(Used(step, key is null ? null : traced.Waited.GetValueOrDefault(key)));

                    break;

                // Claude Code puts no length on a refusal, so this counts only where one was recorded.
                case StepKind.Refused:
                    worked.Add(new Spell(SplitPart.Waiting, step.AtUtc, step.LengthMs));

                    break;
            }
        }

        worked.AddRange(traced.Waited.Values.Select(wait => Spelled(SplitPart.Waiting, wait)));
        worked.AddRange(traced.Hooked.Select(hook => Spelled(SplitPart.Hooks, hook)));
        worked.AddRange(ran.Select(agent => new Spell(SplitPart.Subagents, agent.AtUtc, agent.LengthMs)));

        return worked;
    }

    // The wait for a person sits at the head of the call, so what is left of it is the tool's own work.
    private static Spell Used(Step step, Stretch? waited)
    {
        var ended = Ends(step.AtUtc, step.LengthMs);

        if (waited is null)
        {
            return new Spell(SplitPart.Tools, step.AtUtc, step.LengthMs);
        }

        var allowed = Ends(waited.AtUtc, waited.LengthMs);
        var ran = allowed < step.AtUtc ? step.AtUtc : allowed > ended ? ended : allowed;

        return new Spell(SplitPart.Tools, ran, (long)(ended - ran).TotalMilliseconds);
    }

    private static Spell Spelled(SplitPart part, Stretch stretch) => new(part, stretch.AtUtc, stretch.LengthMs);

    private static bool Aside(EventLine line) =>
        line.Attribute(EventAttributes.QuerySource) is { Length: > 0 } source && source != MainAgent;

    private static IReadOnlyList<Spell> Idle(OpenedRun opened, IReadOnlyList<Spell> worked)
    {
        var run = opened.Run!;
        var quiet = opened.Said.Select(said => new Spell(SplitPart.Quiet, said.AtUtc, said.LengthMs)).ToList();

        // A Turn's start is worked back from its length, so a Step can begin before the run's first event.
        var from = worked.Concat(quiet).Select(spell => spell.AtUtc).Append(run.StartedUtc).Min();
        var to = worked.Concat(quiet).Select(spell => Ends(spell.AtUtc, spell.LengthMs))
            .Append(Ends(run.StartedUtc, run.LengthMs))
            .Max();

        return [.. quiet, new Spell(SplitPart.YourTurn, from, (long)(to - from).TotalMilliseconds)];
    }

    private static IReadOnlyList<Spell> Apart(IReadOnlyList<Spell> spells)
    {
        var starting = spells.Where(spell => spell.LengthMs > 0).OrderBy(spell => spell.AtUtc).ToList();

        var edges = starting
            .SelectMany(spell => new[] { spell.AtUtc, Ends(spell.AtUtc, spell.LengthMs) })
            .Distinct()
            .Order()
            .ToList();

        var open = new List<Spell>();
        var apart = new List<Spell>();
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
    private static void Took(List<Spell> apart, SplitPart part, DateTimeOffset from, DateTimeOffset to)
    {
        if (apart.Count > 0 &&
            apart[^1].Part == part &&
            Ends(apart[^1].AtUtc, apart[^1].LengthMs) == from)
        {
            apart[^1] = apart[^1] with { LengthMs = (long)(to - apart[^1].AtUtc).TotalMilliseconds };

            return;
        }

        apart.Add(new Spell(part, from, (long)(to - from).TotalMilliseconds));
    }

    private static DateTimeOffset Ends(DateTimeOffset at, long lengthMs) => at.AddMilliseconds(lengthMs);
}
