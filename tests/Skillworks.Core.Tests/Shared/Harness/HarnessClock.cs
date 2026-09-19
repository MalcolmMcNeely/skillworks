using Microsoft.Extensions.Time.Testing;

namespace Skillworks.Core.Tests.Shared.Harness;

public static class HarnessClock
{
    // Dated where the fixtures are, or a fixture and the Clock a host reads could land on different days.
    public static FakeTimeProvider Still() => new(Recently.Now);
}
