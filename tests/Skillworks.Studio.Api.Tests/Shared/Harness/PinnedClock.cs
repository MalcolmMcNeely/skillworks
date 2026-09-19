using Skillworks.Core.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Harness;

// A clock that stood still would never let a timeout in a test fire.
public sealed class PinnedClock : TimeProvider
{
    private readonly long _started;

    public PinnedClock() => _started = GetTimestamp();

    public override DateTimeOffset GetUtcNow() => Recently.Now + GetElapsedTime(_started);
}
