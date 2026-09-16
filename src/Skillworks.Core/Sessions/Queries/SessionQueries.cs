using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Sessions.Queries;

public sealed class SessionQueries(EventsStoreReader events, TimeProvider clock)
{
    private const string TitleEvent = "assistant_response";

    private const string PromptEvent = "user_prompt";

    private const string ToolCallEvent = "tool_result";

    // Claude Code writes no tool_result for a call that never ran, so a refusal is only ever a decision.
    private const string DecisionEvent = "tool_decision";

    private const string ModelErrorEvent = "api_error";

    private const string TurnEvent = "api_request";

    // The only event a Skill's name reaches, so the runs it fired in are read from these alone.
    private const string FiringEvent = "skill_activated";

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

    private static readonly string[] ByTitle = [EventAttributes.Session, EventAttributes.Response];

    private static readonly string[] ByPrompt = [EventAttributes.Session, EventAttributes.Prompt];

    // One read answers how many Tool calls a run made and how many of them failed.
    private static readonly string[] ByOutcome = [EventAttributes.Session, SuccessAttribute];

    private static readonly string[] ByDecision = [EventAttributes.Session, DecisionAttribute];

    // Totals, never a list of events: a busy organisation's week is more lines than one read holds.
    public async Task<(IReadOnlyList<Session> Sessions, EventTotals Period)> ListAsync(
        DaySpan span,
        Filter filter,
        SessionOrder order,
        CancellationToken cancellationToken)
    {
        var everything = Events(span, filter);

        var placing = events.CountAsync(everything, ByWhereabouts, cancellationToken);
        var starting = events.EarliestAsync(everything, BySession, cancellationToken);
        var ending = events.LatestAsync(everything, BySession, cancellationToken);
        var titling = events.EarliestAsync(Titles(span, filter), ByTitle, cancellationToken);
        var prompting = events.EarliestAsync(everything with { EventName = PromptEvent }, ByPrompt, cancellationToken);
        var calling = events.CountAsync(everything with { EventName = ToolCallEvent }, ByOutcome, cancellationToken);
        var deciding = events.CountAsync(everything with { EventName = DecisionEvent }, ByDecision, cancellationToken);
        var erring = events.CountAsync(everything with { EventName = ModelErrorEvent }, BySession, cancellationToken);
        var costing = events.SumAsync(everything with { EventName = TurnEvent }, CostAttribute, BySession, cancellationToken);

        var firing = filter.Skill is null
            ? Task.FromResult(EventTotals.Of([]))
            : events.CountAsync(Firings(span, filter), BySession, cancellationToken);

        // Judged on the period, not on what was asked, or a Repository with no runs would read as a quiet week.
        var surveying = filter.Repository is null ? placing : events.CountAsync(Events(span), [], cancellationToken);

        var read = new Readings(
            await placing,
            await starting,
            await ending,
            await titling,
            await prompting,
            await calling,
            await deciding,
            await erring,
            await costing,
            await firing,
            await surveying);

        var period = read.Surveyed with { Unreachable = read.Unreachable };

        return (period.Unreachable is null ? Rows(read, filter, order) : [], period);
    }

    private IReadOnlyList<Session> Rows(Readings read, Filter filter, SessionOrder order)
    {
        var (firstEvent, lastEvent) = (MomentsOf(read.Started), MomentsOf(read.Ended));
        var titles = WordsOf(read.Titled, EventAttributes.Response);
        var prompts = WordsOf(read.Prompted, EventAttributes.Prompt);
        var toolCalls = CountedIn(read.Called.Groups);
        var toolFaults = CountedIn(read.Called.Groups.Where(Failed));
        var modelFaults = CountedIn(read.Erred.Groups);
        var friction = CountedIn(read.Decided.Groups.Where(Refused));
        var costs = SummedIn(read.Cost);
        var now = clock.GetUtcNow();

        // A Skill says which runs are listed, never how much of a run is counted.
        var firedIn = filter.Skill is null ? null : Keyed(read.Fired);

        var sessions =
            from run in Identified(read.Placed.Groups)
            let id = run.Key
            where firstEvent.ContainsKey(id) && lastEvent.ContainsKey(id)
            where firedIn is null || firedIn.Contains(id)
            let repository = MostlySaid(run, total => total.Repository)
            let startedAt = firstEvent[id]
            select new Session(
                id,
                startedAt,
                repository,
                MostlySaid(run, total => total.Attribute(EventAttributes.Person)),
                SessionName.Of(titles.GetValueOrDefault(id), prompts.GetValueOrDefault(id), repository, startedAt),
                (long)(lastEvent[id] - startedAt).TotalMilliseconds,
                RunningWindow.Covers(lastEvent[id], now),
                toolCalls.GetValueOrDefault(id),
                costs.GetValueOrDefault(id),
                toolFaults.GetValueOrDefault(id) + modelFaults.GetValueOrDefault(id),
                friction.GetValueOrDefault(id));

        return order.Sorted(sessions);
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

    private static Dictionary<string, int> CountedIn(IEnumerable<EventTotal> groups) =>
        Identified(groups).ToDictionary(run => run.Key, run => (int)run.Sum(total => total.Total));

    private static Dictionary<string, decimal> SummedIn(EventTotals totals) =>
        Identified(totals.Groups).ToDictionary(run => run.Key, run => run.Sum(total => total.Total));

    private static HashSet<string> Keyed(EventTotals totals) =>
        [.. Identified(totals.Groups).Select(run => run.Key)];

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
    private static EventQuery Firings(DaySpan span, Filter filter) =>
        Events(span) with { EventName = FiringEvent, Skill = filter.Skill };

    // One short of an answer is no answer, as a run missing its name or its length would read as a lie.
    private sealed record Readings(
        EventTotals Placed,
        EventTotals Started,
        EventTotals Ended,
        EventTotals Titled,
        EventTotals Prompted,
        EventTotals Called,
        EventTotals Decided,
        EventTotals Erred,
        EventTotals Cost,
        EventTotals Fired,
        EventTotals Surveyed)
    {
        public string? Unreachable =>
            Placed.Unreachable ?? Started.Unreachable ?? Ended.Unreachable ?? Titled.Unreachable ??
            Prompted.Unreachable ?? Called.Unreachable ?? Decided.Unreachable ?? Erred.Unreachable ??
            Cost.Unreachable ?? Fired.Unreachable ?? Surveyed.Unreachable;
    }
}
