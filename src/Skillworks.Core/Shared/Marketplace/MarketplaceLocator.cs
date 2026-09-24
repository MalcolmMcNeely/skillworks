using Microsoft.Extensions.Options;

namespace Skillworks.Core.Shared.Marketplace;

public sealed class MarketplaceLocator(IOptions<MarketplaceOptions> options)
{
    public MarketplaceLocation Locate()
    {
        var path = Path.GetFullPath(options.Value.Path);
        return new MarketplaceLocation(path, Directory.Exists(path));
    }
}
