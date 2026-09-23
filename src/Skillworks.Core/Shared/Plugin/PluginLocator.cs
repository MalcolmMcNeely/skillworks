using Microsoft.Extensions.Options;

namespace Skillworks.Core.Shared.Plugin;

public sealed class PluginLocator(IOptions<PluginOptions> options)
{
    public PluginLocation Locate()
    {
        var path = Path.GetFullPath(options.Value.Path);
        return new PluginLocation(path, Directory.Exists(path));
    }
}
