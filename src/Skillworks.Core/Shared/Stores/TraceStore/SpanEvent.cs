namespace Skillworks.Core.Shared.Stores.TraceStore;

public sealed record SpanEvent(string Name, IReadOnlyDictionary<string, string> Attributes);
