using Microsoft.EntityFrameworkCore;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// The price table, read whole on every query and written a row at a time. Reading it whole is
/// cheap — it holds one row per model — and it is what lets a corrected price show up in the next
/// answer rather than in the next ingest.
/// </summary>
public sealed class PriceTable(IDbContextFactory<TelemetryDbContext> contexts)
{
    public async Task<IReadOnlyList<ModelPrice>> PricesAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        return await store.ModelPrices.OrderBy(price => price.Model).ToListAsync(cancellationToken);
    }

    /// <summary>
    /// Keyed exactly as a transcript spells the model. A near miss is a row the developer has not
    /// written yet, and reporting that cost as partial is true; matching it loosely would only have
    /// to guess which of two rows was meant.
    /// </summary>
    public async Task<IReadOnlyDictionary<string, ModelPrice>> ByModelAsync(CancellationToken cancellationToken) =>
        (await PricesAsync(cancellationToken)).ToDictionary(price => price.Model);

    /// <summary>Sets one model's price, naming a model the table has never heard of if need be.</summary>
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
