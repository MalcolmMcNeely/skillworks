namespace Skillworks.Core.TraceStore;

// The trace store falls short on its own, so this reason is never the events store's.
public sealed record SessionSpans(IReadOnlyList<Span> Spans, string? Unreachable, bool Shortened)
{
    public static SessionSpans Of(IReadOnlyList<Span> spans, bool shortened) => new(spans, null, shortened);

    public static SessionSpans Failed(string reason) => new([], reason, false);
}
