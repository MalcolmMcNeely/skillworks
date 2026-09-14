namespace Skillworks.Core.Ingest;

public readonly record struct IngestPass(int TranscriptsRead, int ActivationsAdded, bool Full);
