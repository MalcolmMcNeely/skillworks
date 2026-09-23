using Skillworks.Core.Shared.Plugin;

namespace Skillworks.Studio.Api.Shared.Plugin;

public static class PluginEndpoints
{
    public static IEndpointRouteBuilder MapPluginEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("plugin", (PluginLocator locator) => locator.Locate());

        return api;
    }
}
