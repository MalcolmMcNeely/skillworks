using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

public sealed record ActivationOpened(ActivationSummary? Activation, ProvenanceNote Provenance);
