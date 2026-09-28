using Skillworks.Core.Sessions.DepthColumn;
using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class SessionQueries(EventsStoreReader events, TraceStoreReader traces)
{
    private const string TitleEvent = "assistant_response";

    private const string PromptEvent = "user_prompt";

    // The only event a Skill's name reaches, so the runs it activated in are read from these alone.
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

    private static readonly string[] ByTitle = [EventAttributes.Session, EventAttributes.Response];

    // Every read after the Prompts names the loaded rows, as grouping over every Session ran Loki past its series limit.
    public async Task<SessionsRead> ListAsync(
        DateTimeOffset asOf,
        DateTimeOffset? latestBefore,
        Filter filter,
        CancellationToken cancellationToken)
    {
        var start = latestBefore ?? asOf;
        var heard = await HeardAsync(start, asOf, latestBefore, filter, cancellationToken);

        // Only a read that ran out of lines saw the rest of its 30 days quiet, as one that stopped at fifty never looked.
        var quietSince = heard.ReadToItsEnd ? start - Reach : (DateTimeOffset?)null;

        if (heard.Unreachable is { } unheard)
        {
            return SessionsRead.Failed(unheard, heard.LinesRead);
        }

        if (heard.Works.Count == 0)
        {
            var (unasked, linesRead) = heard.LinesRead == 0 && (filter.Repository ?? filter.Skill) is not null
                ? await UnnarrowedPromptsAsync(start, cancellationToken)
                : (null, heard.LinesRead);

            if (unasked is not null)
            {
                return SessionsRead.Failed(unasked, 0);
            }

            return SessionsRead.Empty(linesRead, quietSince);
        }

        var from = heard.Works.Min(work => work.Latest) - ParentReach;
        var window = new EventQuery(EventQuery.AnyEvent, from, asOf);

        var standing = await StandingAsync(window, heard.Works, cancellationToken);

        if (standing.Unreachable is { } unplaced)
        {
            return SessionsRead.Failed(unplaced, heard.LinesRead);
        }

        var present = Keyed(standing.Groups, EventAttributes.Session);

        Work[] unfolded =
        [
            .. heard.Works
                .SelectMany(work => work.NamedAsParent && !work.Spoke && !present.Contains(work.Id) ? work.Unfolded() : [work])
                .OrderByDescending(work => work.Latest)
                .ThenBy(work => work.Id, StringComparer.Ordinal),
        ];
        Work[] works = [.. FiftyWithTies(unfolded)];

        // Children left past the fifty sit between the Latest and the quiet date, so the next read starts from the Latest.
        if (unfolded.Length > works.Length)
        {
            quietSince = null;
        }

        string[] ids = [.. works.Select(work => work.Id)];
        var own = window with { Sessions = ids };
        var children = window with { Parents = ids };

        // To the end of the day, as the trace store files a Span by when it arrived, which can be after the instant read up to.
        // Named, so a busy period costs the trace store no more than the rows loaded.
        var tracing = traces.OfSessionsAsync(
            works.SelectMany(work => work.Members),
            from,
            DaySpan.Of(DayOf(asOf)).UntilUtc,
            cancellationToken);

        var placing = events.CountAsync(own, ByWhereabouts, cancellationToken);
        var starting = events.EarliestAsync(own, BySession, cancellationToken);
        var ending = events.LatestAsync(own, BySession, cancellationToken);
        var childrenEnding = events.LatestAsync(children, ByParent, cancellationToken);
        var titling = events.EarliestAsync(Titles(own), ByTitle, cancellationToken);

        // Lines, not a total by the words, as every different Prompt would be a series of its own.
        var prompting = events.LinesAsync(own with { EventName = PromptEvent }, cancellationToken);

        var gate = new Gate(
            await placing,
            await starting,
            await ending,
            await childrenEnding,
            await titling,
            await prompting);

        if (gate.Unreachable is { } unreachable)
        {
            return SessionsRead.Failed(unreachable, heard.LinesRead);
        }

        var rows = Rows(gate, works, asOf);

        // Only once the gate is back, so no Measure shares the store with a Gate read and a slow one never costs the rows.
        var measuring = Measuring(own, children, cancellationToken);

        // Taken from the reads that place and name a run, so the words half of a Depth costs no question of its own.
        var withheld = new HashSet<string>(heard.Withheld, StringComparer.Ordinal);
        withheld.UnionWith(gate.Prompted.Lines.Where(Withheld).Select(line => line.Attribute(EventAttributes.Session)!));

        return new SessionsRead(
            null,
            rows,
            LandingAsync(measuring.Values, rows, cancellationToken),
            DepthsAsync(tracing, works, rows, withheld),
            heard.LinesRead,
            quietSince is null ? works[^1].Latest : null,
            quietSince);
    }

    // A later read takes only work older than the Latest it starts from, so work sharing the fiftieth Latest comes along.
    private static IEnumerable<Work> FiftyWithTies(IReadOnlyList<Work> newestFirst) =>
        newestFirst.Where((work, index) => index < RowsPerRead || work.Latest == newestFirst[RowsPerRead - 1].Latest);

    // Behind the rows, so a slow trace store never holds back a table the events store has already answered.
    private static async Task<DepthLanding?> DepthsAsync(
        Task<TracedSessions> tracing,
        IReadOnlyList<Work> works,
        IReadOnlyList<SessionRow> rows,
        IReadOnlySet<string> withheld)
    {
        var traced = await tracing;
        var members = works.ToDictionary(work => work.Id, work => work.Members, StringComparer.Ordinal);
        var depths = new Dictionary<string, Depth>(StringComparer.Ordinal);

        foreach (var row in rows)
        {
            if (DepthOf(members[row.Id], traced, withheld) is { } depth)
            {
                depths[row.Id] = depth;
            }
        }

        return new DepthLanding(depths, traced);
    }

    // Full when the Parent or any one Child is, as the row stands for the whole piece of work.
    // A store that could not be read names no run, so only withheld words still say Thin without it.
    private static Depth? DepthOf(IEnumerable<string> members, TracedSessions traced, IReadOnlySet<string> withheld)
    {
        string[] named = [.. members];

        if (named.Any(member => Depths.Of(traced.Sessions.Contains(member), withheld.Contains(member)) == Depth.Full))
        {
            return Depth.Full;
        }

        return traced.Unreachable is null || named.All(withheld.Contains) ? Depth.Thin : null;
    }

    // Newest first, until fifty pieces of work are held, so a busy week costs no more to read than a quiet one.
    // The Filter narrows the lines of activity in the store, so a read under it brings fifty rows where fifty exist.
    // A Child's line still places its Parent, so the row stands for the whole piece of work.
    private async Task<Heard> HeardAsync(
        DateTimeOffset start,
        DateTimeOffset asOf,
        DateTimeOffset? latestBefore,
        Filter filter,
        CancellationToken cancellationToken)
    {
        var works = new Dictionary<string, Work>(StringComparer.Ordinal);
        var placed = new List<Work>();
        var unasked = new List<Work>();
        var drawn = new HashSet<string>(StringComparer.Ordinal);
        var withheld = new HashSet<string>(StringComparer.Ordinal);
        long linesRead = 0;

        var newest = events.NewestFirstAsync(Activity(start - Reach, start, filter), cancellationToken);

        // Asked of the work heard since the last time, so a later read costs no more however far down the list it is.
        async Task<string?> SetAsideDrawnAsync()
        {
            if (latestBefore is not { } latest || unasked.Count == 0)
            {
                return null;
            }

            var since = await DrawnSinceAsync(
                latest,
                asOf,
                [.. unasked.Select(work => work.Id)],
                filter,
                cancellationToken);

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
                return new Heard(unreachable, linesRead, [], withheld, ReadToItsEnd: false);
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
                    // Work heard at the instant of the oldest held is taken in too, as the next read starts older than it.
                    if (works.Count >= RowsPerRead && line.At < placed[^1].Latest)
                    {
                        if (await SetAsideDrawnAsync() is { } unchecking)
                        {
                            return new Heard(unchecking, linesRead, [], withheld, ReadToItsEnd: false);
                        }

                        if (works.Count >= RowsPerRead)
                        {
                            return new Heard(null, linesRead, placed, withheld, ReadToItsEnd: false);
                        }
                    }

                    works[id] = work = new Work(id, line.At);
                    placed.Add(work);
                    unasked.Add(work);
                }

                linesRead++;
                work.Hear(session, line.At, parent is not null);

                if (line.Attribute(EventAttributes.Prompt) == EventAttributes.Withheld)
                {
                    withheld.Add(session);
                }
            }
        }

        if (await SetAsideDrawnAsync() is { } unsure)
        {
            return new Heard(unsure, linesRead, [], withheld, ReadToItsEnd: false);
        }

        return new Heard(null, linesRead, placed, withheld, ReadToItsEnd: true);
    }

    // Only a page of Prompts read without the Filter tells a quiet store from a narrowed list.
    private async Task<(string? Unreachable, long Prompts)> UnnarrowedPromptsAsync(
        DateTimeOffset start,
        CancellationToken cancellationToken)
    {
        await foreach (var page in events.NewestFirstAsync(new EventQuery(PromptEvent, start - Reach, start), cancellationToken))
        {
            return (page.Unreachable, page.Lines.Count);
        }

        return (null, 0);
    }

    // Work with a line of activity from the Latest up to the as-of instant sat higher in an earlier read, so it was drawn there.
    // Only a line the Filter keeps counts, as the earlier read under it never heard another.
    private async Task<(string? Unreachable, IReadOnlySet<string> Drawn)> DrawnSinceAsync(
        DateTimeOffset latest,
        DateTimeOffset asOf,
        string[] ids,
        Filter filter,
        CancellationToken cancellationToken)
    {
        var since = Activity(latest, asOf, filter);

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

    private static IReadOnlyList<SessionRow> Rows(Gate gate, IReadOnlyList<Work> works, DateTimeOffset asOf)
    {
        var firstEvent = MomentsOf(gate.Started, EventAttributes.Session);
        var lastEvent = MomentsOf(gate.Ended, EventAttributes.Session);
        var childrenEnded = MomentsOf(gate.ChildrenEnded, EventAttributes.Parent);
        var titles = WordsOf(gate.Titled, EventAttributes.Response);
        var prompts = FirstPrompts(gate.Prompted);

        var placed = Grouped(gate.Placed.Groups, EventAttributes.Session).ToDictionary(run => run.Key);

        var rows = new List<SessionRow>();

        foreach (var work in works)
        {
            if (!firstEvent.TryGetValue(work.Id, out var startedAt) || !lastEvent.TryGetValue(work.Id, out var ended))
            {
                continue;
            }

            IReadOnlyList<EventTotal> run = placed.TryGetValue(work.Id, out var said) ? [.. said] : [];

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
                work.Latest,
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

    // Under a Skill its Activations mark activity in place of Prompts, so the work where it activated most recently comes first.
    // A Skill says which runs are listed, never how much of a run is counted, so it narrows these lines and nothing else.
    private static EventQuery Activity(DateTimeOffset from, DateTimeOffset until, Filter filter) =>
        new(filter.Skill is null ? PromptEvent : ActivationEvent, from, until)
        {
            Repository = filter.Repository,
            Skill = filter.Skill,
        };

    private sealed record Heard(
        string? Unreachable,
        long LinesRead,
        IReadOnlyList<Work> Works,
        IReadOnlySet<string> Withheld,
        bool ReadToItsEnd);

    // One short of these is no answer, as a run missing its name or its length would read as a lie.
    private sealed record Gate(
        EventTotals Placed,
        EventTotals Started,
        EventTotals Ended,
        EventTotals ChildrenEnded,
        EventTotals Titled,
        EventLines Prompted)
    {
        public string? Unreachable =>
            Placed.Unreachable ?? Started.Unreachable ?? Ended.Unreachable ?? ChildrenEnded.Unreachable ??
            Titled.Unreachable ?? Prompted.Unreachable;
    }

    // A piece of work as the lines of activity found it: its Latest is the first one heard, which is the newest.
    private sealed class Work(string id, DateTimeOffset latest)
    {
        private readonly Dictionary<string, DateTimeOffset> _members = new(StringComparer.Ordinal);

        public string Id => id;

        public DateTimeOffset Latest => latest;

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
