using Microsoft.Extensions.Options;

namespace Skillworks.Core.Catalogue;

public sealed class CatalogueLocator(IOptions<CatalogueOptions> options)
{
    public CatalogueLocation Locate()
    {
        var path = Path.GetFullPath(options.Value.Path);
        return new CatalogueLocation(path, Directory.Exists(path));
    }
}
