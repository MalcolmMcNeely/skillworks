namespace Skillworks.Architecture;

public sealed record Breach(string Rule, string Path, string Message)
{
    public override string ToString() => $"{Rule} at {Path}: {Message}";

    internal static string OneOf(IEnumerable<string> names)
    {
        var quoted = names.Select(name => $"`{name}`").ToList();

        return quoted switch
        {
            [] => "no folder the rules name",
            [var only] => only,
            _ => $"{string.Join(", ", quoted.SkipLast(1))} or {quoted[^1]}",
        };
    }
}
