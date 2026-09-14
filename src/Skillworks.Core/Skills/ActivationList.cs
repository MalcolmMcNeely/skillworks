using Skillworks.Core.Provenance;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

public sealed record ActivationList(
    IReadOnlyList<ActivationSummary> Activations,
    ProvenanceNote Provenance);
