using Skillworks.Core.Arriving;

namespace Skillworks.Core.Sessions.Measures;

// A run the read never named made none of it, so a row with no value here is a zero rather than a hole.
public sealed record SessionMeasure(Measure Measure, IReadOnlyDictionary<string, decimal> Values)
    : ArrivingLine("measure");
