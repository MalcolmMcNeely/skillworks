using Microsoft.Extensions.Options;

namespace Skillworks.Core.Shared.Stores.EventsStore;

// Not sealed, so a test can see a read join the line, which nothing outside the line can.
public class EventsStoreLine(IOptions<LokiOptions> options)
{
    // A line of none would hold every read for ever, and a semaphore lets out the reads that await it first come, first served.
    private readonly SemaphoreSlim _places = new(Math.Max(1, options.Value.ReadsAtOnce));

    public virtual Task WaitAsync(CancellationToken cancellationToken) => _places.WaitAsync(cancellationToken);

    public void Release() => _places.Release();
}
