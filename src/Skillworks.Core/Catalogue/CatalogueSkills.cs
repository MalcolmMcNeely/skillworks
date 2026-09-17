namespace Skillworks.Core.Catalogue;

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
               // Spelled as Claude Code invokes a plugin skill, or a catalogue name never meets its Activations.
               select $"{Path.GetFileName(plugin)}:{Path.GetFileName(skill)}"
        ];
    }
}
