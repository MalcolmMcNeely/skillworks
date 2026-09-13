namespace Skillworks.Core.Catalogue;

/// <summary>
/// The skills the catalogue holds, named the way Claude Code invokes them. A marketplace is a
/// folder of plugins, and a plugin keeps its skills in <c>skills/&lt;name&gt;/SKILL.md</c>.
/// </summary>
public sealed class CatalogueSkills(CatalogueLocator locator)
{
    public IReadOnlyList<string> Names()
    {
        var catalogue = locator.Locate();

        if (!catalogue.Exists)
        {
            return [];
        }

        return
        [
            .. from plugin in Directory.EnumerateDirectories(catalogue.Path)
               let folder = Path.Combine(plugin, "skills")
               where Directory.Exists(folder)
               from skill in Directory.EnumerateDirectories(folder)
               where File.Exists(Path.Combine(skill, "SKILL.md"))
               select $"{Path.GetFileName(plugin)}:{Path.GetFileName(skill)}"
        ];
    }
}
