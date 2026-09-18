namespace Skillworks.Architecture;

// The words of a name run together, so `PartSpell`, `part_spell` and `part spell` flatten to one text.
internal sealed record Flattened(string Letters, bool[] IsWordEdge, bool[] IsCut)
{
    public static Flattened Of(string text)
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

    public bool Is(Flattened other) =>
        Letters.Length > 0 && Letters == other.Letters && !HasCut && !other.HasCut;

    private bool HasCut => IsCutInside(0, Letters.Length);

    private bool IsCutInside(int at, int length)
    {
        for (var inside = at + 1; inside < at + length; inside++)
        {
            if (IsCut[inside])
                return true;
        }

        return false;
    }

    // The words of a name are joined by nothing, an underscore, a hyphen or one space, and nothing else.
    private static bool Joins(string gap) => gap is "_" or "-" or " ";

    // In a run of capitals only the last starts a word, so HTTPServer is HTTP then Server.
    private static bool StartsAWord(string text, int at) =>
        char.IsUpper(text[at])
        && (!char.IsUpper(text[at - 1]) || (at + 1 < text.Length && char.IsLower(text[at + 1])));
}
