using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Activations;

public sealed record ActivationsPage(IReadOnlyList<Activation> Activations) : ArrivingLine("activations");
