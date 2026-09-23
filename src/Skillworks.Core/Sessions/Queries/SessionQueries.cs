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

    // Totals, never a list of events: a busy organisation's week is more lines than one read holds.
    public async Task<SessionsRead> ListAsync(
        DaySpan span,
        Filter filter,
        SessionOrder order,
        CancellationToken cancellationToken)
    {
        var everything = Events(span, filter);

        // Started with the totals, so a Depth costs a reader no wait the events store was not already taking.
        var tracing = depths.OfPeriodAsync(span, filter, cancellationToken);

        // The gate: issued ahead of the Measures, because Loki runs four queries at a time.
        var placing = events.CountAsync(everything, ByWhereabouts, cancellationToken);
        var starting = events.EarliestAsync(everything, BySession, cancellationToken);
        var ending = events.LatestAsync(everything, BySession, cancellationToken);
        var titling = events.EarliestAsync(Titles(span, filter), ByTitle, cancellationToken);
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

        // Judged on the period, not on what was asked, or a Repository with no runs would read as a quiet week.
        var surveying = filter.Repository is null ? placing : events.CountAsync(Events(span), [], cancellationToken);

        var measuring = new Dictionary<Measure, Task<MeasureLanding>>
        {
            [Measure.ToolCalls] = TotalledAsync(Measure.ToolCalls, calling, read => TotalledIn(read.Groups)),
            [Measure.Cost] = TotalledAsync(Measure.Cost, costing, read => TotalledIn(read.Groups)),
            [Measure.Faults] = FaultsAsync(calling, erring),
            [Measure.Friction] = TotalledAsync(Measure.Friction, deciding, read => TotalledIn(read.Groups.Where(Refused))),
        };

        var gate = new Gate(
            await placing,
            await starting,
            await ending,
            await titling,
            await prompting,
            await parenting,
            await activating);

        // A reader who arrived sorted on a Measure waits for it here, so the rows are drawn once, in that order.
        var ranking = order.SortedMeasure is { } sortedOn ? await measuring[sortedOn] : null;

        var traced = await tracing;

        if ((gate.Unreachable ?? ranking?.Unreachable) is { } unreachable)
        {
            var empty = PeriodAsync(unreachable, surveying, standing: null);

            return new SessionsRead(unreachable, [], AsyncEnumerable.Empty<MeasureLanding>(), empty, traced);
        }

        var rows = Rows(gate, filter, order, traced, ranking?.Values ?? NoValues);

        return new SessionsRead(
            null,
            rows,
            LandingAsync(measuring.Values, rows, cancellationToken),
            PeriodAsync(null, surveying, rows.Count > 0 ? gate.Placed : null),
            traced);
    }

    // Each lands on its own, so nothing ready is held back to buy an order a test could read top to bottom.
    private static async IAsyncEnumerable<MeasureLanding> LandingAsync(
        IEnumerable<Task<MeasureLanding>> measuring,
        IReadOnlyList<SessionRow> rows,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        await foreach (var landing in Task.WhenEach(measuring).WithCancellation(cancellationToken))
        {
            var measured = await landing;

            yield return measured.Unreachable is null ? measured with { Values = Only(rows, measured.Values) } : measured;
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

    // The survey only tells a quiet period from a narrowed one, and rows on the table answer that already,
    // so where they stand the read that named them speaks for a survey that fell short.
    private static async Task<EventTotals> PeriodAsync(string? gated, Task<EventTotals> surveying, EventTotals? standing)
    {
        var surveyed = await surveying;

        if (gated is not null)
        {
            return surveyed with { Unreachable = gated };
        }

        return surveyed.Unreachable is null || standing is null ? surveyed : standing;
    }

    // A run no row names was narrowed away, and handing its figure back would undo the narrowing.
    private static IReadOnlyDictionary<string, decimal> Only(
        IReadOnlyList<SessionRow> rows,
        IReadOnlyDictionary<string, decimal> values) =>
        rows.Where(row => values.ContainsKey(row.Id)).ToDictionary(row => row.Id, row => values[row.Id]);

    private IReadOnlyList<SessionRow> Rows(
        Gate gate,
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

        var standing = Identified(gate.Placed.Groups)
            .Where(run => firstEvent.ContainsKey(run.Key) && lastEvent.ContainsKey(run.Key))
            .ToList();

        var parents = ParentsOf(gate.Parented, [.. standing.Select(run => run.Key)]);

        // A Parent sits idle while its Children work, so its own last event would read the work as finished.
        var workEnded = standing
            .GroupBy(run => parents.GetValueOrDefault(run.Key, run.Key), run => lastEvent[run.Key])
            .ToDictionary(work => work.Key, work => work.Max());

        var sessions =
            from run in standing
            let id = run.Key
            where !parents.ContainsKey(id)
            where firedIn is null || firedIn.Contains(id)
            // Narrowing by a read that fell short would hide runs nobody asked to hide.
            where traced.FellShort || filter.Covers(Depths.Of(traced.Sessions.Contains(id), withheld.Contains(id)))
            let repository = MostlySaid(run, total => total.Repository)
            let startedAt = firstEvent[id]
            select new SessionRow(
                id,
                startedAt,
                repository,
                MostlySaid(run, total => total.Attribute(EventAttributes.Person)),
                SessionName.Of(titles.GetValueOrDefault(id), prompts.GetValueOrDefault(id), repository, startedAt),
                (long)(workEnded[id] - startedAt).TotalMilliseconds,
                RunningWindow.Covers(workEnded[id], now));

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

    // Claude Code names a Repository on every event of a run or on none, so no run is left half read.
    private static EventQuery Events(DaySpan span, Filter filter) => Events(span) with { Repository = filter.Repository };

    private static EventQuery Titles(DaySpan span, Filter filter) =>
        Events(span, filter) with { EventName = TitleEvent, QuerySource = TitleSource };

    // The Repository is left off, as the rows this narrows are narrowed by it already.
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
