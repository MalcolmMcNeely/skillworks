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
            entry => entry.Value.Select(word => (Word: word, Letters: Flatten(word).Letters)).ToList(),
            StringComparer.Ordinal);

        foreach (var file in sourceFiles.Where(file => !rules.Skips(file)))
        {
            if (contexts.ClaimOf(file) is not { } context
                || !bannedIn.TryGetValue(context.Name, out var banned)
                || banned.Count == 0)
                continue;

            var text = Flatten(File.ReadAllText(Path.Combine(root, file)));

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

    private static Flattened Flatten(string text)
    {
        var letters = new char[text.Length];
        var isWordEdge = new bool[text.Length + 1];
        var isCut = new bool[text.Length + 1];
        var length = 0;
        var gapAt = -1;

        for (var at = 0; at < text.Length; at++)
        {
            if (!char.IsLetterOrDigit(text[at]))
            {
                gapAt = gapAt < 0 ? at : gapAt;
                continue;
            }

            if (gapAt >= 0)
            {
                isWordEdge[length] = true;
                isCut[length] = !Joins(text[gapAt..at]);
                gapAt = -1;
            }
            else if (at > 0 && StartsAWord(text, at))
            {
                isWordEdge[length] = true;
            }

            letters[length++] = char.ToLowerInvariant(text[at]);
        }

        isWordEdge[0] = true;
        isWordEdge[length] = true;

        return new Flattened(new string(letters, 0, length), isWordEdge, isCut);
    }

    // The words of a name are joined by nothing, an underscore, a hyphen or one space, and nothing else.
    private static bool Joins(string gap) => gap is "_" or "-" or " ";

    // In a run of capitals only the last starts a word, so HTTPServer is HTTP then Server.
    private static bool StartsAWord(string text, int at) =>
        char.IsUpper(text[at])
        && (!char.IsUpper(text[at - 1]) || (at + 1 < text.Length && char.IsLower(text[at + 1])));

    // The words of a name run together, so `PartSpell`, `part_spell` and `part spell` flatten to one text.
    private sealed record Flattened(string Letters, bool[] IsWordEdge, bool[] IsCut)
    {
        public bool Holds(string word)
        {
            if (word.Length == 0)
                return false;

            for (var at = Letters.IndexOf(word, StringComparison.Ordinal);
                 at >= 0;
                 at = Letters.IndexOf(word, at + 1, StringComparison.Ordinal))
            {
                if (IsWordEdge[at] && IsWordEdge[at + word.Length] && !IsCutInside(at, word.Length))
                    return true;
            }

            return false;
        }

        private bool IsCutInside(int at, int length)
        {
            for (var inside = at + 1; inside < at + length; inside++)
            {
                if (IsCut[inside])
                    return true;
            }

            return false;
        }
    }
}
