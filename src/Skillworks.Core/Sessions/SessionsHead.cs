using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Sessions;

// The span comes before the rows, so the page says which days it covers while they are still being read.
public sealed record SessionsHead(DaySpan Span) : ArrivingLine("head");
