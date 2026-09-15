using Skillworks.Core.Ingest.Queries;

namespace Skillworks.Core.Ingest;

public sealed class IngestReport(IngestState state, TranscriptFaultQueries faults)
{
    public async Task<IngestStatus> StatusAsync(CancellationToken cancellationToken) =>
        state.Status(await faults.CountAsync(cancellationToken));

    public Task<IReadOnlyList<TranscriptFault>> FaultsAsync(CancellationToken cancellationToken) =>
        faults.FaultsAsync(cancellationToken);

    public Task<IngestStatus> RequestPassAsync(bool full, CancellationToken cancellationToken)
    {
        state.RequestPass(full);

        return StatusAsync(cancellationToken);
    }
}
