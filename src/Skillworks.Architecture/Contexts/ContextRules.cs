using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Contexts;

internal sealed record ContextRules(IReadOnlyList<Context> Contexts)
{
    public const string RelativePath = "CONTEXT-MAP.md";

    public static ContextRules Read(RulesFile file) =>
        new(file.RequireEach(
            "contexts",
            "a map from a context name to its `glossary` and its `code` paths",
            (name, context) => new Context(
                name,
                context.RequireText("glossary", "the path of the file that holds the context's words"),
                context.RequireTrueOrFalse("slices"),
                context.RequireList("code"))));

    public Context? ClaimOf(string path) => Contexts.FirstOrDefault(context => context.Claims(path));

    public bool DeclaresSlices(string path) => ClaimOf(path) is { Slices: true };
}
