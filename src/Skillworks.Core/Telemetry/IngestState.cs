namespace Skillworks.Core.Telemetry;

/// <summary>How the ingest is getting on.</summary>
/// <param name="Running">A pass is in flight, or one has been asked for and not started yet.</param>
/// <param name="CompletedPasses">Passes finished since Studio started. Zero means nothing is in yet.</param>
/// <param name="TranscriptsSeen">Files the current or last pass has visited.</param>
/// <param name="TranscriptsTotal">Files that pass set out to visit. The two together are progress.</param>
/// <param name="TranscriptsRead">Files with new content in the last finished pass.</param>
/// <param name="ActivationsAdded">Firings added by the last finished pass.</param>
/// <param name="LastPassWasFull">The last finished pass re-read everything rather than only changes.</param>
/// <param name="LastRefreshUtc">When the numbers on screen last moved. Null means never.</param>
/// <param name="Faults">Lines and files the ingest has had to step over, all passes counted.</param>
public sealed record IngestStatus(
    bool Running,
    int CompletedPasses,
    int TranscriptsSeen,
    int TranscriptsTotal,
    int TranscriptsRead,
    int ActivationsAdded,
    bool LastPassWasFull,
    DateTimeOffset? LastRefreshUtc,
    int Faults);

/// <summary>What woke the ingest loop.</summary>
/// <param name="Asked">Someone asked for this pass, rather than the sweep coming round.</param>
/// <param name="Full">The pass should forget everything already read and read it all again.</param>
public readonly record struct PassRequest(bool Asked, bool Full);

/// <summary>
/// The live state of the ingest, shared between the background service that does the work and the
/// endpoints that report it.
/// </summary>
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

    /// <param name="faults">Counted in the store, which is the only place they survive a restart.</param>
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

    /// <summary>Asks for another pass. Returns at once; the pass happens in the background.</summary>
    /// <param name="full">True asks the next pass to forget everything and read it all again.</param>
    public void RequestPass(bool full)
    {
        lock (_gate)
        {
            _asked++;
            _fullRequested |= full;
        }

        _requests.Release();
    }

    /// <summary>
    /// Waits for a request, giving up after <paramref name="interval"/> so new sessions are picked
    /// up without anyone asking.
    /// </summary>
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

    /// <param name="asked">
    /// True clears one outstanding request, in the same breath as the pass becoming visible as
    /// running. Splitting the two would leave a moment where the ingest looked idle with work owed.
    /// </param>
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

    /// <summary>
    /// The count goes up last, after the numbers behind it are in place, so anyone who sees pass N
    /// also sees what pass N found.
    /// </summary>
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
