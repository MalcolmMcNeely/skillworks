namespace Skillworks.Architecture.Contexts;

internal static class ContextMap
{
    public const string Rule = "contexts";

    public static IEnumerable<Breach> Check(string root, ContextRules rules) =>
    [
        .. MissingGlossaries(root, rules.Contexts),
        .. PathsTwoContextsClaim(rules.Contexts),
    ];

    private static IEnumerable<Breach> MissingGlossaries(string root, IReadOnlyList<Context> contexts) =>
        contexts
            .Where(context => !File.Exists(Path.Combine(root, context.Glossary)))
            .Select(context => new Breach(
                Rule,
                context.Glossary,
                $"Write the glossary `{context.Name}` names, or point `{context.Name}` at the file holding its words."));

    private static IEnumerable<Breach> PathsTwoContextsClaim(IReadOnlyList<Context> contexts)
    {
        var claims = contexts
            .SelectMany(context => context.Code.Select(path => (context.Name, Path: path)))
            .ToList();

        for (var at = 0; at < claims.Count; at++)
        {
            for (var next = at + 1; next < claims.Count; next++)
            {
                var (outer, inner) = (claims[at], claims[next]);

                if (outer.Name == inner.Name)
                    continue;

                if (Context.Covers(inner.Path, outer.Path))
                    (outer, inner) = (inner, outer);

                if (!Context.Covers(outer.Path, inner.Path))
                    continue;

                yield return new Breach(
                    Rule,
                    inner.Path,
                    $"`{outer.Name}` already claims `{outer.Path}`, so drop this path from `{inner.Name}`.");
            }
        }
    }
}
