using System.Runtime.CompilerServices;
using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Sessions.Measures;
using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed class SessionQueries(EventsStoreReader events, DepthQueries depths, TimeProvider clock)
{
    private const string TitleEvent = "assistant_response";

    private const string PromptEvent = "user_prompt";

    private const string ToolCallEvent = "tool_result";

    // Claude Code writes no tool_result for a call that never ran, so a refusal is only ever a decision.
    private const string DecisionEvent = "tool_decision";

    private const string ModelErrorEvent = "api_error";

    private const string TurnEvent = "api_request";

    // The only event a Skill's name reaches, so the runs it fired in are read from these alone.
    private const string ActivationEvent = "skill_activated";

    // The one Turn whose answer is the Session's name.
    private const string TitleSource = "generate_session_title";

    private const string SuccessAttribute = "success";

    private const string DecisionAttribute = "decision";

    private const string CostAttribute = "cost_usd";

    private const string Unsuccessful = "false";

    private const string Rejected = "reject";

    private static readonly string[] BySession = [EventAttributes.Session];

    private static readonly string[] ByWhereabouts =
    [
        EventAttributes.Session,
        EventAttributes.Owner,
        EventAttributes.RepositoryName,
        EventAttributes.Person,
    ];

    private static readonly string[] ByParent = [EventAttributes.Session, EventAttributes.Parent];

    private static readonly string[] ByTitle = [EventAttributes.Session, EventAttributes.Response];

    private static readonly string[] ByPrompt = [EventAttributes.Session, EventAttributes.Prompt];

    // One read answers how many Tool calls a run made and how many of them failed.
    private static readonly string[] ByOutcome = [EventAttributes.Session, SuccessAttribute];

    private static readonly string[] ByDecision = [EventAttributes.Session, DecisionAttribute];

    private static readonly IReadOnlyDictionary<string, decimal> NoValues = new Dictionary<string, decimal>();

    // A Parent waits on its Children for hours, so a week back reaches the start of any Parent still at work.
    private static readonly TimeSpan ParentReach = TimeSpan.FromDays(7);

    // Totals, never a list of events: a busy organisation's week is more lines than one read holds.
    // A Repository is judged here and not in the store, as a Parent row stands for Children in other Repositories.
    public async Task<SessionsRead> ListAsync(
        DaySpan span,
        Filter filter,
        SessionOrder order,
        CancellationToken cancellationToken)
    {
        var everything = Events(span);

        // Started with the totals, so a Depth costs a reader no wait the events store was not already taking.
        var tracing = depths.OfPeriodAsync(span, filter, cancellationToken);

        // The gate: issued ahead of the Measures, because Loki runs four queries at a time.
        var placing = events.CountAsync(everything, ByWhereabouts, cancellationToken);
        var starting = events.EarliestAsync(everything, BySession, cancellationToken);
        var ending = events.LatestAsync(everything, BySession, cancellationToken);
        var titling = events.EarliestAsync(Titles(everything), ByTitle, cancellationToken);
        var prompting = events.EarliestAsync(everything with { EventName = PromptEvent }, ByPrompt, cancellationToken);

        // In the gate too, because a Child folded into its Parent is a row that does not exist.
        var parenting = events.CountAsync(everything with { NamesParent = true }, ByParent, cancellationToken);

        // In the gate too, because a Skill decides which runs are listed.
        var activating = filter.Skill is null
            ? Task.FromResult(EventTotals.Of([]))
            : events.CountAsync(ActivationsIn(span, filter), BySession, cancellationToken);

        var calling = events.CountAsync(everything with { EventName = ToolCallEvent }, ByOutcome, cancellationToken);
        var deciding = events.CountAsync(everything with { EventName = DecisionEvent }, ByDecision, cancellationToken);
        var erring = events.CountAsync(everything with { EventName = ModelErrorEvent }, BySession, cancellationToken);
        var costing = events.SumAsync(everything with { EventName = TurnEvent }, CostAttribute, BySession, cancellationToken);

        var measuring = new Dictionary<Measure, Task<MeasureLanding>>
        {
            [Measure.ToolCalls] = TotalledAsync(Measure.ToolCalls, calling, read => TotalledIn(read.Groups)),
            [Measure.Cost] = TotalledAsync(Measure.Cost, costing, read => TotalledIn(read.Groups)),
            [Measure.Faults] = FaultsAsync(calling, erring),
            [Measure.Friction] = TotalledAsync(Measure.Friction, deciding, read => TotalledIn(read.Groups.Where(Refused))),
        };

        var period = await placing;

        var gate = await WithParentsBeforeSpanAsync(
            new Gate(
                period,
                await starting,
                await ending,
                await titling,
                await prompting,
                await parenting,
                await activating),
            span,
            cancellationToken);

        var standing = Standing(gate);
        var parents = ParentsOf(gate.Parented, standing);

        // A reader who arrived sorted on a Measure waits for it here, so the rows are drawn once, in that order.
        var ranking = order.SortedMeasure is { } sortedOn ? await measuring[sortedOn] : null;

        var traced = await tracing;

        if ((gate.Unreachable ?? ranking?.Unreachable) is { } unreachable)
        {
            return new SessionsRead(
                unreachable,
                [],
                AsyncEnumerable.Empty<MeasureLanding>(),
                period with { Unreachable = unreachable },
                traced);
        }

        var rows = Rows(gate, standing, parents, filter, order, traced, Folded(ranking?.Values ?? NoValues, parents));

        return new SessionsRead(null, rows, LandingAsync(measuring.Values, rows, parents, cancellationToken), period, traced);
    }

    // A Parent that began before the span names and starts its Children's row, even when it spoke inside the span too.
    private async Task<Gate> WithParentsBeforeSpanAsync(Gate gate, DaySpan span, CancellationToken cancellationToken)
    {
        if (gate.Unreachable is not null)
        {
            return gate;
        }

        var standing = Standing(gate);

        string[] named =
        [
            .. gate.Parented.Groups
                .Select(total => total.Attribute(EventAttributes.Parent))
                .OfType<string>()
                .Where(parent => parent.Length > 0)
                .Distinct()
                .Order(StringComparer.Ordinal),
        ];

        if (named.Length == 0)
        {
            return gate;
        }

        string[] outside = [.. named.Where(parent => !standing.Contains(parent))];

        var before = new EventQuery(EventQuery.AnyEvent, span.FromUtc - ParentReach, span.FromUtc) { Sessions = named };

        // Moments fold to the earlier, so a Parent seen inside the span would be cut short, and the span already reads its Repository.
        var placing = outside.Length == 0
            ? Task.FromResult(EventTotals.Of([]))
            : events.CountAsync(before with { Sessions = outside }, ByWhereabouts, cancellationToken);
        var ending = outside.Length == 0
            ? Task.FromResult(EventTotals.Of([]))
            : events.LatestAsync(before with { Sessions = outside }, BySession, cancellationToken);
        var starting = events.EarliestAsync(before, BySession, cancellationToken);
        var titling = events.EarliestAsync(Titles(before), ByTitle, cancellationToken);
        var prompting = events.EarliestAsync(before with { EventName = PromptEvent }, ByPrompt, cancellationToken);

        return gate with
        {
            Placed = gate.Placed.Plus(await placing),
            Started = gate.Started.Plus(await starting),
            Ended = gate.Ended.Plus(await ending),
            Titled = gate.Titled.Plus(await titling),
            Prompted = gate.Prompted.Plus(await prompting),
        };
    }

    // Each lands on its own, so nothing ready is held back to buy an order a test could read top to bottom.
    private static async IAsyncEnumerable<MeasureLanding> LandingAsync(
        IEnumerable<Task<MeasureLanding>> measuring,
        IReadOnlyList<SessionRow> rows,
        IReadOnlyDictionary<string, string> parents,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        await foreach (var landing in Task.WhenEach(measuring).WithCancellation(cancellationToken))
        {
            var measured = await landing;

            yield return measured.Unreachable is null
                ? measured with { Values = Only(rows, Folded(measured.Values, parents)) }
                : measured;
        }
    }

    private static async Task<MeasureLanding> TotalledAsync(
        Measure measure,
        Task<EventTotals> reading,
        Func<EventTotals, IReadOnlyDictionary<string, decimal>> totalled)
    {
        var read = await reading;

        return new MeasureLanding(measure, read.Unreachable is null ? totalled(read) : NoValues, read.Unreachable);
    }

    // Both halves are added before the figure goes out, so a reader never watches the count climb from one to both.
    private static async Task<MeasureLanding> FaultsAsync(Task<EventTotals> calling, Task<EventTotals> erring)
    {
        var (called, erred) = (await calling, await erring);
        var unreachable = called.Unreachable ?? erred.Unreachable;

        var values = unreachable is null
            ? Added(TotalledIn(called.Groups.Where(Failed)), TotalledIn(erred.Groups))
            : NoValues;

        return new MeasureLanding(Measure.Faults, values, unreachable);
    }

    // A run no row names was narrowed away, and handing its figure back would undo the narrowing.
    private static IReadOnlyDictionary<string, decimal> Only(
        IReadOnlyList<SessionRow> rows,
        IReadOnlyDictionary<string, decimal> values) =>
        rows.Where(row => values.ContainsKey(row.Id)).ToDictionary(row => row.Id, row => values[row.Id]);

    // A Parent row stands for the whole piece of work, so each Child's figure is added to its Parent's.
    private static Dictionary<string, decimal> Folded(
        IReadOnlyDictionary<string, decimal> values,
        IReadOnlyDictionary<string, string> parents) =>
        values
            .GroupBy(value => parents.GetValueOrDefault(value.Key, value.Key), value => value.Value)
            .ToDictionary(work => work.Key, work => work.Sum());

    private IReadOnlyList<SessionRow> Rows(
        Gate gate,
        HashSet<string> standing,
        IReadOnlyDictionary<string, string> parents,
        Filter filter,
        SessionOrder order,
        TracedSessions traced,
        IReadOnlyDictionary<string, decimal> ranked)
    {
        var (firstEvent, lastEvent) = (MomentsOf(gate.Started), MomentsOf(gate.Ended));
        var titles = WordsOf(gate.Titled, EventAttributes.Response);
        var prompts = WordsOf(gate.Prompted, EventAttributes.Prompt);
        var now = clock.GetUtcNow();

        // A Skill says which runs are listed, never how much of a run is counted.
        var firedIn = filter.Skill is null ? null : Keyed(gate.Fired.Groups);

        // Taken from the read that names a run, so the words half of a Depth costs no second question.
        var withheld = Keyed(gate.Prompted.Groups.Where(Withheld));

        var runs = Identified(gate.Placed.Groups).Where(run => standing.Contains(run.Key)).ToDictionary(run => run.Key);

        // Each Filter is met when the Parent or any one Child meets it, as the row stands for the whole piece of work.
        var sessions =
            from work in runs.Values.GroupBy(run => parents.GetValueOrDefault(run.Key, run.Key))
            let id = work.Key
            let run = runs[id]
            where filter.Repository is null || work.Any(member => member.Any(total => total.Repository == filter.Repository))
            where firedIn is null || work.Any(member => firedIn.Contains(member.Key))
            // Narrowing by a read that fell short would hide runs nobody asked to hide.
            where traced.FellShort || work.Any(member => filter.Covers(Depths.Of(traced.Sessions.Contains(member.Key), withheld.Contains(member.Key))))
            // A Parent sits idle while its Children work, so its own last event would read the work as finished.
            let workEnded = work.Max(member => lastEvent[member.Key])
            let repository = MostlySaid(run, total => total.Repository)
            let startedAt = firstEvent[id]
            select new SessionRow(
                id,
                startedAt,
                repository,
                MostlySaid(run, total => total.Attribute(EventAttributes.Person)),
                SessionName.Of(titles.GetValueOrDefault(id), prompts.GetValueOrDefault(id), repository, startedAt),
                (long)(workEnded - startedAt).TotalMilliseconds,
                RunningWindow.Covers(workEnded, now));

        return order.Sorted(sessions, ranked);
    }

    // A Parent with no events in the store has no row to take its Children in, so they keep rows of their own.
    private static Dictionary<string, string> ParentsOf(EventTotals parented, HashSet<string> standing) =>
        Identified(parented.Groups)
            .Select(run => (
                Child: run.Key,
                Parent: run
                    .Select(total => total.Attribute(EventAttributes.Parent))
                    .OfType<string>()
                    .Where(parent => parent != run.Key && standing.Contains(parent))
                    .Order(StringComparer.Ordinal)
                    .FirstOrDefault()))
            .Where(link => link.Parent is not null)
            .ToDictionary(link => link.Child, link => link.Parent!);

    private static HashSet<string> Standing(Gate gate)
    {
        var standing = Keyed(gate.Placed.Groups);

        standing.IntersectWith(Keyed(gate.Started.Groups));
        standing.IntersectWith(Keyed(gate.Ended.Groups));

        return standing;
    }

    // An older Claude Code puts the repository on no event, and a run with no origin remote has none.
    // The store returns a run's groups in no order, so what most of its events said wins, and a tie goes by name.
    private static string? MostlySaid(IEnumerable<EventTotal> run, Func<EventTotal, string?> said) =>
        run.GroupBy(said)
            .Where(value => value.Key is not null)
            .OrderByDescending(value => value.Sum(total => total.Total))
            .ThenBy(value => value.Key, StringComparer.Ordinal)
            .Select(value => value.Key)
            .FirstOrDefault();

    private static Dictionary<string, DateTimeOffset> MomentsOf(EventTotals totals) =>
        Identified(totals.Groups)
            .ToDictionary(run => run.Key, run => DateTimeOffset.FromUnixTimeMilliseconds((long)run.Min(total => total.Total)));

    // Each group's total is when the words were said, so the earliest of them wins.
    private static Dictionary<string, string> WordsOf(EventTotals totals, string attribute) =>
        Identified(totals.Groups.Where(total => total.Attribute(attribute) is { Length: > 0 }))
            .ToDictionary(run => run.Key, run => run.MinBy(said => said.Total)!.Attribute(attribute)!);

    private static bool Failed(EventTotal call) => call.Attribute(SuccessAttribute) == Unsuccessful;

    private static bool Refused(EventTotal decision) => decision.Attribute(DecisionAttribute) == Rejected;

    private static bool Withheld(EventTotal prompt) =>
        prompt.Attribute(EventAttributes.Prompt) == EventAttributes.Withheld;

    private static Dictionary<string, decimal> TotalledIn(IEnumerable<EventTotal> groups) =>
        Identified(groups).ToDictionary(run => run.Key, run => run.Sum(total => total.Total));

    private static Dictionary<string, decimal> Added(
        IReadOnlyDictionary<string, decimal> one,
        IReadOnlyDictionary<string, decimal> other) =>
        one.Keys
            .Union(other.Keys)
            .ToDictionary(id => id, id => one.GetValueOrDefault(id) + other.GetValueOrDefault(id));

    private static HashSet<string> Keyed(IEnumerable<EventTotal> groups) =>
        [.. Identified(groups).Select(run => run.Key)];

    private static IEnumerable<IGrouping<string, EventTotal>> Identified(IEnumerable<EventTotal> groups) =>
        from total in groups
        let id = total.Attribute(EventAttributes.Session)
        where id is { Length: > 0 }
        group total by id;

    private static EventQuery Events(DaySpan span) => new(EventQuery.AnyEvent, span.FromUtc, span.UntilUtc);

    private static EventQuery Titles(EventQuery events) => events with { EventName = TitleEvent, QuerySource = TitleSource };

    private static EventQuery ActivationsIn(DaySpan span, Filter filter) =>
        Events(span) with { EventName = ActivationEvent, Skill = filter.Skill };

    // One short of these is no answer, as a run missing its name or its length would read as a lie.
    private sealed record Gate(
        EventTotals Placed,
        EventTotals Started,
        EventTotals Ended,
        EventTotals Titled,
        EventTotals Prompted,
        EventTotals Parented,
        EventTotals Fired)
    {
        public string? Unreachable =>
            Placed.Unreachable ?? Started.Unreachable ?? Ended.Unreachable ?? Titled.Unreachable ??
            Prompted.Unreachable ?? Parented.Unreachable ?? Fired.Unreachable;
    }
}
