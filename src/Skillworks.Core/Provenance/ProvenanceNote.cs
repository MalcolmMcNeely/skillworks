namespace Skillworks.Core.Provenance;

public sealed record ProvenanceNote(ProvenanceGap Gap, string? Missing, DateTimeOffset SinceUtc);
