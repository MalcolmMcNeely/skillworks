using Microsoft.CodeAnalysis.CSharp;
using Skillworks.Architecture.Placement;

namespace Skillworks.Architecture.Comments;

internal static class DocComments
{
    public const string Rule = "doc-comments";

    private static readonly string[] TripleQuotes = ["\"\"\"", "'''"];

    public static IEnumerable<Breach> Check(
        string root,
        IReadOnlyList<string> sourceFiles,
        PlacementRules placement,
        CommentRules comments)
    {
        foreach (var file in sourceFiles)
        {
            if (comments.DocComments && !placement.IsTestFile(Path.GetFileName(file)))
                continue;

            var lines = LinesOfDocComments(file, File.ReadAllText(Path.Combine(root, file)));
            if (lines.Count == 0)
                continue;

            yield return new Breach(
                Rule,
                file,
                $"Remove the doc comments at {Breach.AtLines(lines)}. " +
                "Keep a reason a reader needs as an ordinary comment.");
        }
    }

    private static IReadOnlyList<int> LinesOfDocComments(string file, string text) => Path.GetExtension(file) switch
    {
        ".cs" => CSharpLines(text),
        ".ts" or ".tsx" => TypeScriptLines(text),
        ".py" => PythonLines(text),
        _ => [],
    };

    private static IReadOnlyList<int> CSharpLines(string text)
    {
        var tree = CSharpSyntaxTree.ParseText(text);

        return
        [
            .. tree
                .GetRoot()
                .DescendantTrivia()
                .Where(trivia => SyntaxFacts.IsDocumentationCommentTrivia(trivia.Kind()))
                .Select(trivia => tree.GetLineSpan(trivia.Span).StartLinePosition.Line + 1),
        ];
    }

    // Without a parser, a '/**' mid-line could be in a string or after '//', so only a line start counts.
    private static IReadOnlyList<int> TypeScriptLines(string text)
    {
        var lines = text.Split('\n');
        List<int> starts = [];

        for (var line = 0; line < lines.Length; line++)
        {
            var opening = lines[line].TrimStart();
            if (!opening.StartsWith("/**", StringComparison.Ordinal) || opening.StartsWith("/**/", StringComparison.Ordinal))
                continue;

            var end = line;
            List<string> block = [opening[3..]];
            while (!block[^1].Contains("*/", StringComparison.Ordinal) && end + 1 < lines.Length)
                block.Add(lines[++end]);
            block[^1] = block[^1].Split("*/")[0];

            if (!HoldsOnlyTags(block))
                starts.Add(line + 1);

            line = end;
        }

        return starts;
    }

    // The marks are read in order, so the mark that closes a multi-line value is never read as an opening.
    private static IReadOnlyList<int> PythonLines(string text)
    {
        var lines = text.Split('\n');
        List<int> starts = [];
        var at = 0;

        while (at < text.Length)
        {
            var (mark, opening) = NextTripleQuote(text, at);
            if (opening < 0)
                break;

            var line = LineOf(text, opening);
            if (OnlySpaceBefore(text, opening) && OpensABody(lines, line))
                starts.Add(line);

            var closing = text.IndexOf(mark, opening + mark.Length, StringComparison.Ordinal);
            at = closing < 0 ? text.Length : closing + mark.Length;
        }

        return starts;
    }

    // A docstring can open the file itself, and then there is no code above it to find.
    private static bool OpensABody(IReadOnlyList<string> lines, int line)
    {
        for (var above = line - 2; above >= 0; above--)
        {
            var code = lines[above].Trim();
            if (code.Length == 0 || code.StartsWith('#'))
                continue;

            return code.EndsWith(':');
        }

        return true;
    }

    private static (string Mark, int Opening) NextTripleQuote(string text, int from) =>
        TripleQuotes
            .Select(mark => (Mark: mark, Opening: text.IndexOf(mark, from, StringComparison.Ordinal)))
            .Where(found => found.Opening >= 0)
            .OrderBy(found => found.Opening)
            .FirstOrDefault(("", -1));

    private static bool OnlySpaceBefore(string text, int at)
    {
        for (var back = at - 1; back >= 0 && text[back] != '\n'; back--)
        {
            if (!char.IsWhiteSpace(text[back]))
                return false;
        }

        return true;
    }

    private static int LineOf(string text, int at) => text.AsSpan(0, at).Count('\n') + 1;

    private static bool HoldsOnlyTags(IEnumerable<string> block) =>
        block
            .Select(line => line.Trim().TrimStart('*').Trim())
            .Where(line => line.Length > 0)
            .All(line => line.StartsWith('@'));
}
