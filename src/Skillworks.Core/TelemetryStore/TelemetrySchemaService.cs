using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Hosting;

namespace Skillworks.Core.TelemetryStore;

public sealed class TelemetrySchemaService(IDbContextFactory<TelemetryDbContext> contexts) : IHostedService
{
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);
        await store.Database.MigrateAsync(cancellationToken);
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
