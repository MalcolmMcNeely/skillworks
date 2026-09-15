using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Hosting;

namespace Skillworks.Core.TranscriptStore;

public sealed class TranscriptStoreSchemaService(IDbContextFactory<TranscriptStoreDbContext> contexts) : IHostedService
{
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);
        await store.Database.MigrateAsync(cancellationToken);
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
