using Microsoft.Extensions.Options;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Tests.Shared.Harness;

// No stand-in can see inside Studio's line, so the fact that a read joined it comes from the line itself.
public sealed class HarnessLine(IOptions<LokiOptions> options) : EventsStoreLine(options)
{
    private readonly Lock _gate = new();
    private readonly List<(int Reads, TaskCompletionSource Reached)> _waits = [];

    private int _joined;

    // A test waits for this before it acts on a read that waits its turn, so no test trusts the reader's own order to have put it there.
    public Task JoinedBy(int reads)
    {
        lock (_gate)
        {
            if (_joined >= reads)
            {
                return Task.CompletedTask;
            }

            var reached = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);

            _waits.Add((reads, reached));

            return reached.Task;
        }
    }

    public override Task WaitAsync(CancellationToken cancellationToken)
    {
        // Reported only once the line has taken the read, which it does before the call returns, so the fact never comes early.
        var turn = base.WaitAsync(cancellationToken);

        lock (_gate)
        {
            _joined++;

            foreach (var wait in _waits.Where(wait => wait.Reads <= _joined))
            {
                wait.Reached.TrySetResult();
            }
        }

        return turn;
    }
}
