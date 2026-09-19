using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.Activations;

public sealed record ActivationsPage(IReadOnlyList<Activation> Activations) : ArrivingLine("activations");
