using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class SessionQueries
{
    // Answered in the list's own shape, so the page folds the one row and opens it as it does any other.
    public async Task<SessionsRead> LookupAsync(
        string id,
        DateTimeOffset since,
        DateTimeOffset asOf,
        CancellationToken cancellationToken)
    {
        var newest = await NewestOfAsync(id, since, asOf, cancellationToken);

        if (newest.Unreachable is { } unreachable)
        {
            return SessionsRead.Failed(unreachable, 0);
        }

        if (newest.Lines.Count == 0)
        {
            return SessionsRead.Empty(0, since);
        }

        var latest = newest.Lines.Max(line => line.At);
        var work = new Work(id, latest);

        work.Hear(id, latest, child: false);

        // Read as the list reads a row, so a run older than the lookback still carries its first day.
        var window = new EventQuery(EventQuery.AnyEvent, latest - ParentReach, asOf);

        return await ReadAsync(
            [work],
            window,
            asOf,
            newest.Lines.Count,
            new HashSet<string>(StringComparer.Ordinal),
            oldestLatest: null,
            lookedBackTo: since,
            cancellationToken);
    }

    // A window at a time from today back, and the first that holds the run ends the read, so a recent run never costs the whole reach.
    private async Task<EventLines> NewestOfAsync(
        string id,
        DateTimeOffset since,
        DateTimeOffset asOf,
        CancellationToken cancellationToken)
    {
        var query = new EventQuery(EventQuery.AnyEvent, since, asOf) { Session = id };

        await foreach (var page in events.NewestFirstAsync(query, cancellationToken))
        {
            return page;
        }

        return EventLines.Of([]);
    }
}
