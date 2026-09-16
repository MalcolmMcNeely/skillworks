namespace Skillworks.Core.TraceStore;

public sealed record Span(
    string TraceId,
    string SpanId,
    string? ParentSpanId,
    string Name,
    DateTimeOffset Started,
    DateTimeOffset Ended,
    IReadOnlyDictionary<string, string> Attributes);
