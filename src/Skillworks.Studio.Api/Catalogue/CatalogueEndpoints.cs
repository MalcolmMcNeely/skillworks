using Skillworks.Core.Catalogue;

namespace Skillworks.Studio.Api.Catalogue;

public static class CatalogueEndpoints
{
    public static IEndpointRouteBuilder MapCatalogueEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("catalogue", (CatalogueLocator locator) => locator.Locate());

        return api;
    }
}
