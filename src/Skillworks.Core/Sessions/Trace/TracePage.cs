using Skillworks.Core.Arriving;

namespace Skillworks.Core.Sessions.Trace;

// Step ids alone, as the browser is sent a Session and never a Span.
public sealed record TracePage(IReadOnlyDictionary<string, string> Inside) : ArrivingLine("trace");
