using Skillworks.Core.Sessions.Measures;
using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class SessionQueries(EventsStoreReader events, DepthQueries depths)
{
    private const string TitleEvent = "assistant_response";

    private const string PromptEvent = "user_prompt";

    // The only event a Skill's name reaches, so the runs it fired in are read from these alone.
    private const string ActivationEvent = "skill_activated";

    // The one Turn whose answer is the Session's name.
    private const string TitleSource = "generate_session_title";

    private const int RowsPerRead = 50;

    // Loki refuses a range over 30 days, which sets how far back one read looks.
    private static readonly TimeSpan Reach = TimeSpan.FromDays(30);

    // A Parent waits on its Children for hours, so a week back reaches the start of any Parent still at work.
    private static readonly TimeSpan ParentReach = TimeSpan.FromDays(7);

    private static readonly string[] BySession = [EventAttributes.Session];

    private static readonly string[] ByParent = [EventAttributes.Parent];

    private static readonly string[] ByWhereabouts =
    [
        EventAttributes.Session,
        EventAttributes.Owner,
        EventAttributes.RepositoryName,
        EventAttributes.Person,
    ];

    private static readonly string[] ByParentWhereabouts =
    [
        EventAttributes.Parent,
        EventAttributes.Owner,
        EventAttributes.RepositoryName,
    ];

    private static readonly string[] ByTitle = [EventAttributes.Session, EventAttributes.Response];

    // Every read after the Prompts names the loaded rows, as grouping over every Session ran Loki past its series limit.
    // A Repository and a Skill are judged here and not in the store, as a Parent row stands for Children elsewhere.
    public async Task<SessionsRead> ListAsync(
        DateTimeOffset asOf,
        DateTimeOffset? before,
        Filter filter,
        CancellationToken cancellationToken)
    {
        var heard = await HeardAsync(asOf, before, cancellationToken);

        if (heard.Unreachable is { } unheard)
        {
            return SessionsRead.Failed(unheard, heard.Prompts);
        }

        if (heard.Works.Count == 0)
        {
            return new SessionsRead(
                null,
                [],
                AsyncEnumerable.Empty<MeasureLanding>(),
                heard.Prompts,
                null,
                TracedSessions.Unasked);
        }

        var from = heard.Works.Min(work => work.Place) - ParentReach;
        var window = new EventQuery(EventQuery.AnyEvent, from, asOf);

        var standing = await StandingAsync(window, heard.Works, cancellationToken);

        if (standing.Unreachable is { } unplaced)
        {
            return SessionsRead.Failed(unplaced, heard.Prompts);
        }

        var present = Keyed(standing.Groups, EventAttributes.Session);

        Work[] works =
        [
            .. heard.Works
                .SelectMany(work => work.NamedAsParent && !work.Spoke && !present.Contains(work.Id) ? work.Unfolded() : [work])
                .OrderByDescending(work => work.Place)
                .ThenBy(work => work.Id, StringComparer.Ordinal)
                .Take(RowsPerRead),
        ];

        string[] ids = [.. works.Select(work => work.Id)];
        var own = window with { Sessions = ids };
        var children = window with { Parents = ids };

        // To the end of the day, as the trace store files a Span by when it arrived, which can be after the instant read up to.
        var tracing = depths.OfPeriodAsync(from, DaySpan.Of(DayOf(asOf)).UntilUtc, filter, cancellationToken);

        // The gate: issued ahead of the Measures, because Loki runs four queries at a time.
        var placing = events.CountAsync(own, ByWhereabouts, cancellationToken);
        var starting = events.EarliestAsync(own, BySession, cancellationToken);
        var ending = events.LatestAsync(own, BySession, cancellationToken);
        var childrenEnding = events.LatestAsync(children, ByParent, cancellationToken);
        var titling = events.EarliestAsync(Titles(own), ByTitle, cancellationToken);

        // Lines, not a total by the words, as every different Prompt would be a series of its own.
        var prompting = events.LinesAsync(own with { EventName = PromptEvent }, cancellationToken);

        var childrenPlacing = filter.Repository is null
            ? Task.FromResult(EventTotals.Of([]))
            : events.CountAsync(children, ByParentWhereabouts, cancellationToken);
        var activating = filter.Skill is null
            ? Task.FromResult(EventTotals.Of([]))
            : events.CountAsync(Activations(own, filter), BySession, cancellationToken);
        var childrenActivating = filter.Skill is null
            ? Task.FromResult(EventTotals.Of([]))
            : events.CountAsync(Activations(children, filter), ByParent, cancellationToken);

        var measuring = Measuring(own, children, cancellationToken);

        var gate = new Gate(
            await placing,
            await starting,
            await ending,
            await childrenEnding,
            await titling,
            await prompting,
            await childrenPlacing,
            await activating,
            await childrenActivating);

        var traced = await tracing;

        if (gate.Unreachable is { } unreachable)
        {
            return SessionsRead.Failed(unreachable, heard.Prompts) with { Traced = traced };
        }

        var rows = Rows(gate, works, filter, traced, heard.Withheld, asOf);

        return new SessionsRead(
            null,
            rows,
            LandingAsync(measuring.Values, rows, cancellationToken),
            heard.Prompts,
            works[^1].Place,
            traced);
    }

    // Newest first, until fifty pieces of work are held, so a busy week costs no more to read than a quiet one.
    private async Task<Heard> HeardAsync(DateTimeOffset asOf, DateTimeOffset? before, CancellationToken cancellationToken)
    {
        var works = new Dictionary<string, Work>(StringComparer.Ordinal);
        var placed = new List<Work>();
        var unasked = new List<Work>();
        var drawn = new HashSet<string>(StringComparer.Ordinal);
        var withheld = new HashSet<string>(StringComparer.Ordinal);
        long prompts = 0;

        var start = before ?? asOf;
        var newest = events.NewestFirstAsync(new EventQuery(PromptEvent, start - Reach, start), cancellationToken);

        // Asked of the work heard since the last time, so a later read costs no more however far down the list it is.
        async Task<string?> SetAsideDrawnAsync()
        {
            if (before is not { } place || unasked.Count == 0)
            {
                return null;
            }

            var since = await DrawnSinceAsync(place, asOf, [.. unasked.Select(work => work.Id)], cancellationToken);

            unasked.Clear();

            if (since.Unreachable is not null)
            {
                return since.Unreachable;
            }

            drawn.UnionWith(since.Drawn);
            placed.RemoveAll(work => since.Drawn.Contains(work.Id));

            foreach (var id in since.Drawn)
            {
                works.Remove(id);
            }

            return null;
        }

        await foreach (var page in newest)
        {
            if (page.Unreachable is { } unreachable)
            {
                return new Heard(unreachable, prompts, [], withheld);
            }

            foreach (var line in page.Lines)
            {
                if (line.Attribute(EventAttributes.Session) is not { Length: > 0 } session)
                {
                    continue;
                }

                // A Child's Prompt places its Parent, as the Parent's row stands for the whole piece of work.
                var parent = line.Attribute(EventAttributes.Parent) is { Length: > 0 } named && named != session
                    ? named
                    : null;
                var id = parent ?? session;

                if (drawn.Contains(id))
                {
                    continue;
                }

                if (!works.TryGetValue(id, out var work))
                {
                    if (works.Count == RowsPerRead)
                    {
                        if (await SetAsideDrawnAsync() is { } unchecking)
                        {
                            return new Heard(unchecking, prompts, [], withheld);
                        }

                        if (works.Count == RowsPerRead)
                        {
                            return new Heard(null, prompts, placed, withheld);
                        }
                    }

                    works[id] = work = new Work(id, line.At);
                    placed.Add(work);
                    unasked.Add(work);
                }

                prompts++;
                work.Hear(session, line.At, parent is not null);

                if (line.Attribute(EventAttributes.Prompt) == EventAttributes.Withheld)
                {
                    withheld.Add(session);
                }
            }
        }

        if (await SetAsideDrawnAsync() is { } unsure)
        {
            return new Heard(unsure, prompts, [], withheld);
        }

        return new Heard(null, prompts, placed, withheld);
    }

    // Work with a Prompt from the place up to the as-of instant sat higher in an earlier read, so it was drawn there.
    private async Task<(string? Unreachable, IReadOnlySet<string> Drawn)> DrawnSinceAsync(
        DateTimeOffset place,
        DateTimeOffset asOf,
        string[] ids,
        CancellationToken cancellationToken)
    {
        var since = new EventQuery(PromptEvent, place, asOf);

        var own = events.CountAsync(since with { Sessions = ids }, BySession, cancellationToken);
        var children = events.CountAsync(since with { Parents = ids }, ByParent, cancellationToken);

        var (spoke, asked) = (await own, await children);

        if ((spoke.Unreachable ?? asked.Unreachable) is { } unreachable)
        {
            return (unreachable, new HashSet<string>());
        }

        var drawn = Keyed(spoke.Groups, EventAttributes.Session);
        drawn.UnionWith(Keyed(asked.Groups, EventAttributes.Parent));

        return (null, drawn);
    }

    // A Parent with no events in the store has no row to take its Children in, so they keep rows of their own.
    private Task<EventTotals> StandingAsync(
        EventQuery window,
        IEnumerable<Work> works,
        CancellationToken cancellationToken)
    {
        string[] named = [.. works.Where(work => work.NamedAsParent && !work.Spoke).Select(work => work.Id)];

        return named.Length == 0
            ? Task.FromResult(EventTotals.Of([]))
            : events.CountAsync(window with { Sessions = named }, BySession, cancellationToken);
    }

    private static IReadOnlyList<SessionRow> Rows(
        Gate gate,
        IReadOnlyList<Work> works,
        Filter filter,
        TracedSessions traced,
        IReadOnlySet<string> withheldHeard,
        DateTimeOffset asOf)
    {
        var firstEvent = MomentsOf(gate.Started, EventAttributes.Session);
        var lastEvent = MomentsOf(gate.Ended, EventAttributes.Session);
        var childrenEnded = MomentsOf(gate.ChildrenEnded, EventAttributes.Parent);
        var titles = WordsOf(gate.Titled, EventAttributes.Response);
        var prompts = FirstPrompts(gate.Prompted);

        // Taken from the reads that place and name a run, so the words half of a Depth costs no question of its own.
        var withheld = new HashSet<string>(withheldHeard, StringComparer.Ordinal);
        withheld.UnionWith(gate.Prompted.Lines.Where(Withheld).Select(line => line.Attribute(EventAttributes.Session)!));

        var placed = Grouped(gate.Placed.Groups, EventAttributes.Session).ToDictionary(run => run.Key);
        var childrenPlaced = Grouped(gate.ChildrenPlaced.Groups, EventAttributes.Parent).ToDictionary(work => work.Key);

        // A Skill says which runs are listed, never how much of a run is counted.
        var fired = Keyed(gate.Fired.Groups, EventAttributes.Session);
        fired.UnionWith(Keyed(gate.ChildrenFired.Groups, EventAttributes.Parent));

        var rows = new List<SessionRow>();

        foreach (var work in works)
        {
            if (!firstEvent.TryGetValue(work.Id, out var startedAt) || !lastEvent.TryGetValue(work.Id, out var ended))
            {
                continue;
            }

            IReadOnlyList<EventTotal> run = placed.TryGetValue(work.Id, out var said) ? [.. said] : [];
            IReadOnlyList<EventTotal> elsewhere = childrenPlaced.TryGetValue(work.Id, out var told) ? [.. told] : [];

            // Each Filter is met when the Parent or any one Child meets it, as the row stands for the whole piece of work.
            var kept =
                (filter.Repository is null || run.Concat(elsewhere).Any(total => total.Repository == filter.Repository)) &&
                (filter.Skill is null || fired.Contains(work.Id)) &&
                // Narrowing by a read that fell short would hide runs nobody asked to hide.
                (traced.FellShort || work.Members.Any(member =>
                    filter.Covers(Depths.Of(traced.Sessions.Contains(member), withheld.Contains(member)))));

            if (!kept)
            {
                continue;
            }

            // A Parent sits idle while its Children work, so its own last event would read the work as finished.
            var workEnded = childrenEnded.TryGetValue(work.Id, out var childEnded) && childEnded > ended ? childEnded : ended;
            var repository = MostlySaid(run, total => total.Repository);

            rows.Add(new SessionRow(
                work.Id,
                startedAt,
                repository,
                MostlySaid(run, total => total.Attribute(EventAttributes.Person)),
                SessionName.Of(titles.GetValueOrDefault(work.Id), prompts.GetValueOrDefault(work.Id), repository, startedAt),
                (long)(workEnded - startedAt).TotalMilliseconds,
                RunningWindow.Covers(workEnded, asOf),
                work.Place,
                DayOf(startedAt),
                DayOf(workEnded)));
        }

        return rows;
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

    private static Dictionary<string, DateTimeOffset> MomentsOf(EventTotals totals, string attribute) =>
        Grouped(totals.Groups, attribute)
            .ToDictionary(run => run.Key, run => DateTimeOffset.FromUnixTimeMilliseconds((long)run.Min(total => total.Total)));

    // Each group's total is when the words were said, so the earliest of them wins.
    private static Dictionary<string, string> WordsOf(EventTotals totals, string attribute) =>
        Grouped(totals.Groups.Where(total => total.Attribute(attribute) is { Length: > 0 }), EventAttributes.Session)
            .ToDictionary(run => run.Key, run => run.MinBy(said => said.Total)!.Attribute(attribute)!);

    private static Dictionary<string, string> FirstPrompts(EventLines prompted) =>
        prompted.Lines
            .Where(line => line.Attribute(EventAttributes.Session) is { Length: > 0 } &&
                           line.Attribute(EventAttributes.Prompt) is { Length: > 0 })
            .GroupBy(line => line.Attribute(EventAttributes.Session)!)
            .ToDictionary(run => run.Key, run => run.MinBy(line => line.At)!.Attribute(EventAttributes.Prompt)!);

    private static bool Withheld(EventLine prompt) =>
        prompt.Attribute(EventAttributes.Session) is { Length: > 0 } &&
        prompt.Attribute(EventAttributes.Prompt) == EventAttributes.Withheld;

    private static DateOnly DayOf(DateTimeOffset moment) => DateOnly.FromDateTime(moment.UtcDateTime);

    private static HashSet<string> Keyed(IEnumerable<EventTotal> groups, string attribute) =>
        [.. Grouped(groups, attribute).Select(run => run.Key)];

    private static IEnumerable<IGrouping<string, EventTotal>> Grouped(IEnumerable<EventTotal> groups, string attribute) =>
        from total in groups
        let id = total.Attribute(attribute)
        where id is { Length: > 0 }
        group total by id;

    private static EventQuery Titles(EventQuery events) => events with { EventName = TitleEvent, QuerySource = TitleSource };

    private static EventQuery Activations(EventQuery events, Filter filter) =>
        events with { EventName = ActivationEvent, Skill = filter.Skill };

    private sealed record Heard(string? Unreachable, long Prompts, IReadOnlyList<Work> Works, IReadOnlySet<string> Withheld);

    // One short of these is no answer, as a run missing its name or its length would read as a lie.
    private sealed record Gate(
        EventTotals Placed,
        EventTotals Started,
        EventTotals Ended,
        EventTotals ChildrenEnded,
        EventTotals Titled,
        EventLines Prompted,
        EventTotals ChildrenPlaced,
        EventTotals Fired,
        EventTotals ChildrenFired)
    {
        public string? Unreachable =>
            Placed.Unreachable ?? Started.Unreachable ?? Ended.Unreachable ?? ChildrenEnded.Unreachable ??
            Titled.Unreachable ?? Prompted.Unreachable ?? ChildrenPlaced.Unreachable ?? Fired.Unreachable ??
            ChildrenFired.Unreachable;
    }

    // A piece of work as the Prompts found it: its place is the first Prompt heard, which is the newest.
    private sealed class Work(string id, DateTimeOffset place)
    {
        private readonly Dictionary<string, DateTimeOffset> _members = new(StringComparer.Ordinal);

        public string Id => id;

        public DateTimeOffset Place => place;

        public bool NamedAsParent { get; private set; }

        public bool Spoke => _members.ContainsKey(id);

        public IEnumerable<string> Members => _members.Keys.Append(id).Distinct(StringComparer.Ordinal);

        public void Hear(string session, DateTimeOffset at, bool child)
        {
            NamedAsParent |= child;
            _members.TryAdd(session, at);
        }

        // Each Child keeps its own newest Prompt, so a row of its own sits where its own work does.
        public IEnumerable<Work> Unfolded() =>
            _members.Select(member =>
            {
                var alone = new Work(member.Key, member.Value);

                alone.Hear(member.Key, member.Value, child: false);

                return alone;
            });
    }
}
