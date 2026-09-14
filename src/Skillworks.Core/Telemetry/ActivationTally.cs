namespace Skillworks.Core.Telemetry;

public sealed record ActivationTally(
    IReadOnlyDictionary<string, int> Counts,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Repositories,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Branches,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Models,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Efforts);
