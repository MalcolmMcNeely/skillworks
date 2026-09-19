using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Sessions;

// Carries the resolved order, not the one asked for, so a heading marks the column the answer really used.
public sealed record SessionsHead(DaySpan Span, string Sort, bool Descending) : ArrivingLine("head");
