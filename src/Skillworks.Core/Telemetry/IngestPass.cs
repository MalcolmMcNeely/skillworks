namespace Skillworks.Core.Telemetry;

public readonly record struct IngestPass(int TranscriptsRead, int ActivationsAdded, bool Full);
