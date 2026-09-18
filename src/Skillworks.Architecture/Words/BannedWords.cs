using Skillworks.Architecture.Contexts;

namespace Skillworks.Architecture.Words;

internal static class BannedWords
{
    public const string Rule = "banned-words";

    public static IEnumerable<Breach> Check(
        string root,
        IReadOnlyList<string> sourceFiles,
        WordRules rules,
        ContextRules contexts)
    {
        foreach (var breach in ListsThatMatchNoContext(rules, contexts))
            yield return breach;

        var bannedIn = rules.BannedWords.ToDictionary(
            entry => entry.Key,
            entry => entry.Value.Select(word => (Word: word, Letters: Flattened.Of(word).Letters)).ToList(),
            StringComparer.Ordinal);

        foreach (var file in sourceFiles.Where(file => !rules.Skips(file)))
        {
            if (contexts.ClaimOf(file) is not { } context
                || !bannedIn.TryGetValue(context.Name, out var banned)
                || banned.Count == 0)
                continue;

            var text = Flattened.Of(File.ReadAllText(Path.Combine(root, file)));

            foreach (var entry in banned.Where(entry => text.Holds(entry.Letters)))
            {
                yield return new Breach(
                    Rule,
                    file,
                    $"Replace `{entry.Word}` with the word `{context.Glossary}` settles on.");
            }
        }
    }

    // A list under a name no context carries, or a context with no list, judges nothing and says nothing.
    private static IEnumerable<Breach> ListsThatMatchNoContext(WordRules rules, ContextRules contexts)
    {
        foreach (var name in rules.BannedWords.Keys
            .Where(name => contexts.Contexts.All(context => context.Name != name))
            .Order(StringComparer.Ordinal))
        {
            yield return new Breach(
                Rule,
                WordRules.RelativePath,
                $"`{name}` names no context in `{ContextRules.RelativePath}`, so drop it or add the context.");
        }

        foreach (var context in contexts.Contexts.Where(context => !rules.BannedWords.ContainsKey(context.Name)))
        {
            yield return new Breach(
                Rule,
                WordRules.RelativePath,
                $"Add `{context.Name}` to `banned-words`, set to the words that lost in it, or to `[]`.");
        }
    }
}
