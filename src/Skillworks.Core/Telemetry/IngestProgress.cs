namespace Skillworks.Core.Telemetry;

public readonly record struct IngestProgress(int TranscriptsSeen, int TranscriptsTotal);
