namespace Skillworks.Core.Telemetry;

/// <summary>How the ingest is getting on, and the only way to ask it for another pass.</summary>
/// <param name="Running">A pass is in flight right now.</param>
/// <param name="CompletedPasses">Passes finished since Studio started. Zero means nothing is in yet.</param>
/// <param name="TranscriptsRead">Files with new content in the last finished pass.</param>
/// <param name="ActivationsAdded">Firings added by the last finished pass.</param>
public sealed record IngestStatus(
    bool Running,
    int CompletedPasses,
    int TranscriptsRead,
    int ActivationsAdded);

/// <summary>
/// The live state of the ingest, shared between the background service that does the work and the
/// endpoints that report it.
/// </summary>
public sealed class IngestState
{
    private readonly SemaphoreSlim _requests = new(0);
    private readonly Lock _gate = new();

    private bool _running;
    private int _completedPasses;
    private IngestPass _lastPass;

    public IngestStatus Status()
    {
        lock (_gate)
        {
            return new IngestStatus(
                _running,
                _completedPasses,
                _lastPass.TranscriptsRead,
                _lastPass.ActivationsAdded);
        }
    }

    /// <summary>Asks for another pass. Returns at once; the pass happens in the background.</summary>
    public void RequestPass() => _requests.Release();

    public Task WaitForRequestAsync(CancellationToken cancellationToken) =>
        _requests.WaitAsync(cancellationToken);

    public void PassStarted()
    {
        lock (_gate)
        {
            _running = true;
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
            _running = false;
            _completedPasses++;
        }
    }
}
