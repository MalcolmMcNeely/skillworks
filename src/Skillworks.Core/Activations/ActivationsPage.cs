using Skillworks.Core.Arriving;

namespace Skillworks.Core.Activations;

public sealed record ActivationsPage(IReadOnlyList<Activation> Activations) : ArrivingLine("activations");
