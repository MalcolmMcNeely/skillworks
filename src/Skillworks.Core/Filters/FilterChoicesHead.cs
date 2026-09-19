using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Filters;

public sealed record FilterChoicesHead(DaySpan Span, IReadOnlyList<DateOnly> Days) : ArrivingLine("head");
