namespace Skillworks.Architecture.RulesFiles;

internal static class SkippedFolders
{
    public static bool Holds(IReadOnlyList<string> entries, string folderPath)
    {
        var folderName = folderPath[(folderPath.LastIndexOf('/') + 1)..];

        return entries.Any(entry => entry.Contains('/', StringComparison.Ordinal)
            ? string.Equals(entry, folderPath, StringComparison.Ordinal)
            : string.Equals(entry, folderName, StringComparison.Ordinal));
    }

    public static bool HoldAnyFolderAbove(IReadOnlyList<string> entries, string filePath)
    {
        for (var slash = filePath.IndexOf('/'); slash >= 0; slash = filePath.IndexOf('/', slash + 1))
        {
            if (Holds(entries, filePath[..slash]))
                return true;
        }

        return false;
    }
}
