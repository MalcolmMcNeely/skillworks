namespace Skillworks.Architecture;

public sealed record CheckResult(IReadOnlyList<Breach> Breaches, int SourceFilesScanned);
