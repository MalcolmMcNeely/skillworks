using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Hosting;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// Brings the SQLite file up to the current schema before anything is served. Registered ahead of
/// the ingest so no query and no pass can meet a missing table.
/// </summary>
public sealed class TelemetrySchemaService(IDbContextFactory<TelemetryDbContext> contexts) : IHostedService
{
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);
        await store.Database.MigrateAsync(cancellationToken);
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
