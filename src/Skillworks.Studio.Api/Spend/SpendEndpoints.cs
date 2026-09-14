using Skillworks.Core.Telemetry;

namespace Skillworks.Studio.Api.Spend;

public static class SpendEndpoints
{
    public static IEndpointRouteBuilder MapSpendEndpoints(this IEndpointRouteBuilder api)
    {
        // No filter: prices are configuration read on every skill query, not telemetry.
        api.MapGet("prices", (PriceTable prices, CancellationToken cancellationToken) =>
            prices.PricesAsync(cancellationToken));

        api.MapPut("prices", async (ModelPrice price, PriceTable prices, CancellationToken cancellationToken) =>
            Results.Ok(await prices.SetAsync(price, cancellationToken)));

        return api;
    }
}
