using Microsoft.EntityFrameworkCore;
using Skillworks.Core.TranscriptStore;

namespace Skillworks.Core.Spend;

// Not cached: one row per model is cheap to read, and a corrected price must show in the next answer.
public sealed class PriceTable(IDbContextFactory<TranscriptStoreDbContext> contexts)
{
    public async Task<IReadOnlyList<ModelPrice>> PricesAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        return await store.ModelPrices.OrderBy(price => price.Model).ToListAsync(cancellationToken);
    }

    public async Task<ModelPrice> SetAsync(ModelPrice price, CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);
        var existing = await store.ModelPrices.FindAsync([price.Model], cancellationToken);

        if (existing is null)
        {
            store.ModelPrices.Add(price);
        }
        else
        {
            existing.InputPerMillion = price.InputPerMillion;
            existing.OutputPerMillion = price.OutputPerMillion;
            existing.CacheReadPerMillion = price.CacheReadPerMillion;
            existing.CacheWrite5mPerMillion = price.CacheWrite5mPerMillion;
            existing.CacheWrite1hPerMillion = price.CacheWrite1hPerMillion;
        }

        await store.SaveChangesAsync(cancellationToken);

        return price;
    }
}
