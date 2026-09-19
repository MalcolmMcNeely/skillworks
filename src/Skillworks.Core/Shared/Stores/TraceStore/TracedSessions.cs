namespace Skillworks.Core.Shared.Stores.TraceStore;

// The trace store falls short on its own, so this reason is never the events store's.
public sealed record TracedSessions(IReadOnlySet<string> Sessions, string? Unreachable, bool Shortened)
{
    // A read that fell short names no run it did not reach, so nothing may be narrowed by it.
    public bool FellShort => Unreachable is not null || Shortened;

    public static TracedSessions Unasked => new(Empty, null, false);

    public static TracedSessions Of(IReadOnlySet<string> sessions, bool shortened) => new(sessions, null, shortened);

    public static TracedSessions Failed(string reason) => new(Empty, reason, false);

    private static HashSet<string> Empty => new(StringComparer.Ordinal);
}
