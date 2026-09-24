namespace Skillworks.Core.Shared.Marketplace;

public sealed class MarketplaceSkills(MarketplaceLocator locator)
{
    public IReadOnlyList<string> Names()
    {
        var location = locator.Locate();

        if (!location.Exists)
        {
            return [];
        }

        return
        [
            .. from plugin in Directory.EnumerateDirectories(location.Path)
               let folder = Path.Combine(plugin, "skills")
               where Directory.Exists(folder)
               from skill in Directory.EnumerateDirectories(folder)
               where File.Exists(Path.Combine(skill, "SKILL.md"))
               // Spelled as Claude Code invokes a plugin skill, or a listed name never meets its Activations.
               select $"{Path.GetFileName(plugin)}:{Path.GetFileName(skill)}"
        ];
    }
}
