namespace Skillworks.Core.TraceStore;

// The trace store falls short on its own, so this reason is never the events store's.
public sealed record TracedSessions(IReadOnlySet<string> Sessions, string? Unreachable)
{
    public static TracedSessions Unasked => new(Empty, null);

    public static TracedSessions Of(IReadOnlySet<string> sessions) => new(sessions, null);

    public static TracedSessions Failed(string reason) => new(Empty, reason);

    private static HashSet<string> Empty => new(StringComparer.Ordinal);
}
