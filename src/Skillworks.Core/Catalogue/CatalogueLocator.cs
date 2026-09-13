using Microsoft.Extensions.Options;

namespace Skillworks.Core.Catalogue;

/// <summary>Resolves the configured catalogue path and reports whether it is present.</summary>
public sealed class CatalogueLocator(IOptions<CatalogueOptions> options)
{
    public CatalogueLocation Locate()
    {
        var path = Path.GetFullPath(options.Value.Path);
        return new CatalogueLocation(path, Directory.Exists(path));
    }
}
