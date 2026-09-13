using Skillworks.Core.Provenance;

namespace Skillworks.Core.Skills;

/// <summary>
/// The skill table as one answer: what fired, from where, and what it cost. The note travels with
/// the rows rather than being asked for separately, because a row the events store knows nothing
/// about and a store that could not be read look identical on a screen.
/// </summary>
public sealed record SkillTable(IReadOnlyList<SkillSummary> Skills, ProvenanceNote Provenance);
