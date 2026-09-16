using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Sessions.Queries;

public sealed class SessionQueries(EventsStoreReader events, TimeProvider clock)
{
    private const string TitleEvent = "assistant_response";

    private const string PromptEvent = "user_prompt";

    // The one Turn whose answer is the Session's name.
    private const string TitleSource = "generate_session_title";

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

    // Totals, never a list of events: a busy organisation's week is more lines than one read holds.
    public async Task<(IReadOnlyList<Session> Sessions, EventTotals Period)> ListAsync(
        DaySpan span,
        CancellationToken cancellationToken)
    {
        var everything = Events(span);

        var placing = events.CountAsync(everything, ByWhereabouts, cancellationToken);
        var starting = events.EarliestAsync(everything, BySession, cancellationToken);
        var ending = events.LatestAsync(everything, BySession, cancellationToken);
        var titling = events.EarliestAsync(Titles(span), ByTitle, cancellationToken);
        var prompting = events.EarliestAsync(everything with { EventName = PromptEvent }, ByPrompt, cancellationToken);

        var read = new Readings(await placing, await starting, await ending, await titling, await prompting);

        // The whereabouts count every event of the span, so it is the period the Gap is judged on.
        var period = read.Placed with { Unreachable = read.Unreachable };

        return (period.Unreachable is null ? Rows(read) : [], period);
    }

    private IReadOnlyList<Session> Rows(Readings read)
    {
        var (firstEvent, lastEvent) = (MomentsOf(read.Started), MomentsOf(read.Ended));
        var titles = WordsOf(read.Titled, EventAttributes.Response);
        var prompts = WordsOf(read.Prompted, EventAttributes.Prompt);
        var now = clock.GetUtcNow();

        var sessions =
            from run in Identified(read.Placed.Groups)
            let id = run.Key
            where firstEvent.ContainsKey(id) && lastEvent.ContainsKey(id)
            let repository = MostlySaid(run, total => total.Repository)
            let startedAt = firstEvent[id]
            select new Session(
                id,
                startedAt,
                repository,
                MostlySaid(run, total => total.Attribute(EventAttributes.Person)),
                SessionName.Of(titles.GetValueOrDefault(id), prompts.GetValueOrDefault(id), repository, startedAt),
                (long)(lastEvent[id] - startedAt).TotalMilliseconds,
                RunningWindow.Covers(lastEvent[id], now));

        // The id breaks a tie, so two runs that started in one millisecond read the same way twice.
        return [.. sessions.OrderByDescending(session => session.StartedUtc).ThenBy(session => session.Id, StringComparer.Ordinal)];
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

    private static IEnumerable<IGrouping<string, EventTotal>> Identified(IEnumerable<EventTotal> groups) =>
        from total in groups
        let id = total.Attribute(EventAttributes.Session)
        where id is { Length: > 0 }
        group total by id;

    private static EventQuery Events(DaySpan span) => new(EventQuery.AnyEvent, span.FromUtc, span.UntilUtc);

    private static EventQuery Titles(DaySpan span) =>
        Events(span) with { EventName = TitleEvent, QuerySource = TitleSource };

    // One short of an answer is no answer, as a run missing its name or its length would read as a lie.
    private sealed record Readings(
        EventTotals Placed,
        EventTotals Started,
        EventTotals Ended,
        EventTotals Titled,
        EventTotals Prompted)
    {
        public string? Unreachable =>
            Placed.Unreachable ?? Started.Unreachable ?? Ended.Unreachable ?? Titled.Unreachable ?? Prompted.Unreachable;
    }
}
