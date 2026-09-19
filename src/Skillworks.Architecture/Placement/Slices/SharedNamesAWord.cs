using Skillworks.Architecture.Contexts;

namespace Skillworks.Architecture.Placement.Slices;

internal static class SharedNamesAWord
{
    public const string Rule = "shared-names-a-word";

    public static IEnumerable<Breach> Check(
        string root,
        IReadOnlyList<string> sourceFiles,
        PlacementRules rules,
        ContextRules contexts)
    {
        var glossaries = GlossariesIn(root, contexts);

        foreach (var folder in CodeRoot.FoldersUnder(root, sourceFiles))
        {
            if (folder.Level != 2 || !rules.IsShared(folder.ParentName, folder.Root.IsFrontEnd))
                continue;

            if (contexts.ClaimOf(folder.Folder) is not { } context
                || !glossaries.TryGetValue(context.Name, out var glossary)
                || glossary.Names(folder.Name))
                continue;

            yield return new Breach(
                Rule,
                folder.Folder,
                $"`{folder.Name}` is not a word in `{context.Glossary}`. Rename this folder to the word its " +
                $"code names, or settle that word in `{context.Glossary}` first.");
        }
    }

    // A glossary that is not there is already a `contexts` breach, so this rule does not say it twice.
    private static IReadOnlyDictionary<string, Glossary> GlossariesIn(string root, ContextRules contexts) =>
        contexts.Contexts
            .Select(context => (context.Name, File: Path.Combine(root, context.Glossary)))
            .Where(context => File.Exists(context.File))
            .ToDictionary(context => context.Name, context => Glossary.Read(context.File), StringComparer.Ordinal);
}
