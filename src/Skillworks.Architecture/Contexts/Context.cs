namespace Skillworks.Architecture.Contexts;

internal sealed record Context(string Name, string Glossary, bool Slices, IReadOnlyList<string> Code)
{
    public bool Claims(string path) => Code.Any(folder => Covers(folder, path));

    public static bool Covers(string folder, string path) =>
        path.StartsWith(folder, StringComparison.Ordinal)
        && (path.Length == folder.Length || path[folder.Length] == '/');
}
