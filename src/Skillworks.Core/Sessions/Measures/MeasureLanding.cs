namespace Skillworks.Core.Sessions.Measures;

// A Measure lands whole or falls short whole, so one stream carries both and nothing is dropped unsaid.
public sealed record MeasureLanding(Measure Measure, IReadOnlyDictionary<string, decimal> Values, string? Unreachable);
