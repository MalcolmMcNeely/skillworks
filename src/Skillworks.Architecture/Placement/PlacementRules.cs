using System.IO.Enumeration;
using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Placement;

internal sealed record PlacementRules(
    IReadOnlyList<string> Slices,
    IReadOnlyList<string> Concerns,
    int MaxTypesPerFolder,
    IReadOnlyList<string> SourceFiles,
    IReadOnlyList<string> TestFiles,
    IReadOnlyList<string> SkipFolders,
    IReadOnlyList<string> BannedFolderNames,
    IReadOnlyDictionary<string, string> NameMap)
{
    public const string RelativePath = ".claude/rules/file-placement.md";

    private const string Shared = "Shared";

    public static PlacementRules Read(RulesFile file)
    {
        var slices = file.RequireList("slices");
        var concerns = file.RequireList("concerns");
        var maxTypesPerFolder = file.RequireWholeNumber("max-types-per-folder");
        var sourceFiles = file.RequireList("source-files");
        var testFiles = file.RequireList("test-files");
        var skipFolders = file.RequireList("skip-folders");
        var bannedFolderNames = file.RequireList("banned-folder-names");
        var nameMap = file.RequireMap(
            "name-map",
            "a map from a name with `*` at the start or the end to a folder name, such as {\"*Queries\": Queries}",
            IsNamePattern);

        return new(
            slices,
            concerns,
            maxTypesPerFolder,
            sourceFiles,
            testFiles,
            skipFolders,
            bannedFolderNames,
            nameMap);
    }

    public string SharedFolderName(bool frontEnd) => InCase(Shared, frontEnd);

    public string SliceFolderName(string slice, bool frontEnd) => InCase(slice, frontEnd);

    public IReadOnlyList<string> SliceAndSharedNames(bool frontEnd) =>
        [.. Slices.Select(name => InCase(name, frontEnd)), SharedFolderName(frontEnd)];

    public bool IsSlice(string folderName, bool frontEnd) =>
        Slices.Any(name => InCase(name, frontEnd) == folderName);

    public bool IsShared(string folderName, bool frontEnd) => folderName == SharedFolderName(frontEnd);

    public bool IsSliceOrShared(string folderName, bool frontEnd) =>
        IsSlice(folderName, frontEnd) || IsShared(folderName, frontEnd);

    public bool IsSharedInAnyCase(string folderName) =>
        string.Equals(folderName, Shared, StringComparison.OrdinalIgnoreCase);

    public string? SliceNamedInAnyCase(string folderName) =>
        Slices.FirstOrDefault(name => string.Equals(name, folderName, StringComparison.OrdinalIgnoreCase));

    public bool IsConcern(string folderName) => Concerns.Contains(folderName, StringComparer.Ordinal);

    public bool IsSourceFile(string fileName) =>
        SourceFiles.Any(suffix => fileName.EndsWith(suffix, StringComparison.Ordinal));

    public bool IsTestFile(string fileName) => TestPatternOf(fileName) is not null;

    public SourceFileName NameOf(string fileName)
    {
        var testPattern = TestPatternOf(fileName);

        // Only a pattern of `*` then fixed text shows where the test marker starts; any other shape cuts at the extension.
        var stem = testPattern is ['*', .. var marker] && marker.IndexOfAny(['*', '?']) < 0
            ? fileName[..^marker.Length]
            : Path.GetFileNameWithoutExtension(fileName);

        var dot = stem.IndexOf('.');

        return new SourceFileName(dot < 0 ? stem : stem[..dot], IsTest: testPattern is not null, HasAspect: dot >= 0);
    }

    public string SubjectOf(string path) => NameOf(Path.GetFileName(path)).Subject;

    public bool IsSkipped(string folderName) => SkipFolders.Contains(folderName, StringComparer.Ordinal);

    public bool IsBanned(string folderName) => BannedFolderNames.Contains(folderName, StringComparer.OrdinalIgnoreCase);

    public IReadOnlyList<(string Pattern, string Folder)> NameMapEntriesMatching(string subject) =>
        [
            .. NameMap
                .Where(entry => entry.Key[0] == '*'
                    ? subject.EndsWith(entry.Key[1..], StringComparison.Ordinal)
                    : subject.StartsWith(entry.Key[..^1], StringComparison.Ordinal))
                .Select(entry => (Pattern: entry.Key, Folder: entry.Value)),
        ];

    // A Slice keeps its name in each language's own case.
    private static string InCase(string name, bool frontEnd) => frontEnd ? name.ToLowerInvariant() : name;

    private static bool IsNamePattern(string pattern) =>
        pattern.Length > 1 && pattern.AsSpan().Count('*') == 1 && (pattern[0] == '*' || pattern[^1] == '*');

    private string? TestPatternOf(string fileName) =>
        TestFiles.FirstOrDefault(pattern => FileSystemName.MatchesSimpleExpression(pattern, fileName, ignoreCase: false));
}
