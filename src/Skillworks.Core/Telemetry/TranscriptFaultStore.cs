using Microsoft.EntityFrameworkCore;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// Reads back what the ingest had to step over. It sits beside the ingest that writes the faults,
/// so the store's shape is known in one place.
/// </summary>
public sealed class TranscriptFaultStore(IDbContextFactory<TelemetryDbContext> contexts)
{
    /// <summary>
    /// The most faults one read hands back. "One bad line" and "every file is corrupt" call for the
    /// same action, and the second should not arrive as a download.
    /// </summary>
    public const int Cap = 200;

    public async Task<int> CountAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        return await store.TranscriptFaults.CountAsync(cancellationToken);
    }

    /// <summary>
    /// Grouped by file and then in line order, which is the order a developer would work through
    /// them. SQLite will not sort a DateTimeOffset, and when it was noticed is the lesser fact.
    /// </summary>
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
