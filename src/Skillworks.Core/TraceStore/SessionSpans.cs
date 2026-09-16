namespace Skillworks.Core.TraceStore;

// The trace store falls short on its own, so this reason is never the events store's.
public sealed record SessionSpans(IReadOnlyList<Span> Spans, string? Unreachable)
{
    public static SessionSpans Of(IReadOnlyList<Span> spans) => new(spans, null);

    public static SessionSpans Failed(string reason) => new([], reason);
}
