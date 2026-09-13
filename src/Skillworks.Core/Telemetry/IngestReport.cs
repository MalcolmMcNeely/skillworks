namespace Skillworks.Core.Telemetry;

/// <summary>
/// One answer to "how is the ingest doing, and can I trust what I am looking at". The pass in
/// flight lives in memory and the faults live in the store, so the two are joined here rather than
/// in the shell that serves them.
/// </summary>
public sealed class IngestReport(IngestState state, TranscriptFaultStore faults)
{
    public async Task<IngestStatus> StatusAsync(CancellationToken cancellationToken) =>
        state.Status(await faults.CountAsync(cancellationToken));

    public Task<IReadOnlyList<TranscriptFault>> FaultsAsync(CancellationToken cancellationToken) =>
        faults.FaultsAsync(cancellationToken);

    /// <summary>
    /// Asks for a pass and hands back the state as it stands. The pass itself happens in the
    /// background, so the status returned is the one to poll from, not the answer.
    /// </summary>
    public Task<IngestStatus> RequestPassAsync(bool full, CancellationToken cancellationToken)
    {
        state.RequestPass(full);

        return StatusAsync(cancellationToken);
    }
}
