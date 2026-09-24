using Skillworks.Core.Shared.Marketplace;

namespace Skillworks.Studio.Api.Shared.Marketplace;

public static class MarketplaceEndpoints
{
    public static IEndpointRouteBuilder MapMarketplaceEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("marketplace", (MarketplaceLocator locator) => locator.Locate());

        return api;
    }
}
