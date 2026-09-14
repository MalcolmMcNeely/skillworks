using Skillworks.Core.Provenance;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

public sealed record ActivationOpened(ActivationDetail Activation, ProvenanceNote Provenance);
