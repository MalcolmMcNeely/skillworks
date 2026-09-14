using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

public sealed record ActivationOpened(ActivationDetail Activation, ProvenanceNote Provenance);
