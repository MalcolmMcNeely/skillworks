namespace Skillworks.Core.Health;

// WhyEmpty covers the transcript half only: provenance explains its own gaps in its ProvenanceNote.
public sealed record HealthReport(IReadOnlyList<StudioPart> Parts, string? WhyEmpty);
