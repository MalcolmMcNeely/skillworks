using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis.CSharp;
using Skillworks.Architecture.Placement;

namespace Skillworks.Architecture.Comments;

internal static class DocComments
{
    public const string Rule = "doc-comments";

    // Only after a line start, a space or punctuation, so a glob such as 'src/**' in a string is not a block.
    private static readonly Regex TypeScriptBlock = new(
        @"(?<=^|[\s(\[{=,:;?!&|>])/\*\*(?!/)(.*?)\*/",
        RegexOptions.Multiline | RegexOptions.Singleline);

    // A tool reads a tag, a {type} and one name or value; any more words are prose for a person.
    private static readonly Regex TagLine = new(@"^@[\w-]+(\s+\{.*\})?(\s+\S+)?$");

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
                $"Remove the doc comments at {(lines.Count == 1 ? "line" : "lines")} {string.Join(", ", lines)}. " +
                "Keep a reason a reader needs as an ordinary comment.");
        }
    }

    private static IReadOnlyList<int> LinesOfDocComments(string file, string text) => Path.GetExtension(file) switch
    {
        ".cs" => CSharpLines(text),
        ".ts" or ".tsx" => TypeScriptLines(text),
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

    private static IReadOnlyList<int> TypeScriptLines(string text) =>
    [
        .. TypeScriptBlock
            .Matches(text)
            .Where(block => !HoldsOnlyTags(block.Groups[1].Value))
            .Select(block => text.AsSpan(0, block.Index).Count('\n') + 1),
    ];

    private static bool HoldsOnlyTags(string block) =>
        block
            .Split('\n')
            .Select(line => line.Trim().TrimStart('*').Trim())
            .Where(line => line.Length > 0)
            .All(TagLine.IsMatch);
}
