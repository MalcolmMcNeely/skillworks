using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Shared.Filters;

public sealed record FilterChoicesHead(DaySpan Span, IReadOnlyList<DateOnly> Days) : ArrivingLine("head");
