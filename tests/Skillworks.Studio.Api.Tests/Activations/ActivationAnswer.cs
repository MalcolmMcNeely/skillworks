using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed record ActivationAnswer
{
    public required ActivationRow? Activation { get; init; }

    public required GapRow Gap { get; init; }
}
