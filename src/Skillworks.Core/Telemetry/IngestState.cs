namespace Skillworks.Core.Telemetry;

public sealed class IngestState(TimeProvider clock)
{
    private readonly SemaphoreSlim _requests = new(0);
    private readonly Lock _gate = new();

    private bool _running;
    private bool _fullRequested;
    private int _asked;
    private int _completedPasses;
    private IngestPass _lastPass;
    private IngestProgress _progress;
    private DateTimeOffset? _lastRefreshUtc;

    public IngestStatus Status(int faults)
    {
        lock (_gate)
        {
            return new IngestStatus(
                // A pass that has been asked for but has not woken up yet is still the ingest being
                // busy. Reporting it as idle invites a second click on a 678 MB re-read.
                _running || _asked > 0,
                _completedPasses,
                _progress.TranscriptsSeen,
                _progress.TranscriptsTotal,
                _lastPass.TranscriptsRead,
                _lastPass.ActivationsAdded,
                _lastPass.Full,
                _lastRefreshUtc,
                faults);
        }
    }

    public void RequestPass(bool full)
    {
        lock (_gate)
        {
            _asked++;
            _fullRequested |= full;
        }

        _requests.Release();
    }

    public async Task<PassRequest> WaitForRequestAsync(TimeSpan interval, CancellationToken cancellationToken)
    {
        var asked = await _requests.WaitAsync(interval, cancellationToken);

        lock (_gate)
        {
            var full = _fullRequested;
            _fullRequested = false;

            return new PassRequest(asked, full);
        }
    }

    // Cleared under the lock that marks the pass running, so the ingest never looks idle with work owed.
    public void PassStarted(bool asked)
    {
        lock (_gate)
        {
            if (asked && _asked > 0)
            {
                _asked--;
            }

            _running = true;
            _progress = default;
        }
    }

    public void PassProgressed(IngestProgress progress)
    {
        lock (_gate)
        {
            _progress = progress;
        }
    }

    public void PassFinished(IngestPass pass)
    {
        lock (_gate)
        {
            _lastPass = pass;
            _lastRefreshUtc = clock.GetUtcNow();
            _running = false;
            _completedPasses++;
        }
    }
}
