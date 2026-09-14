using Microsoft.EntityFrameworkCore;
using Skillworks.Core.TelemetryStore;

namespace Skillworks.Core.Ingest.Stores;

public sealed class TranscriptFaultStore(IDbContextFactory<TelemetryDbContext> contexts)
{
    // "One bad line" and "every file is corrupt" call for the same action; the second need not be a download.
    public const int Cap = 200;

    public async Task<int> CountAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        return await store.TranscriptFaults.CountAsync(cancellationToken);
    }

    public async Task<IReadOnlyList<TranscriptFault>> FaultsAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        return await store.TranscriptFaults
            .OrderBy(fault => fault.Path)
            .ThenBy(fault => fault.Line)
            .Take(Cap)
            .ToListAsync(cancellationToken);
    }
}
