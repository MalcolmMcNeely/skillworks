using System.IO.Enumeration;
using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Placement;

internal sealed record PlacementRules(
    int MaxTypesPerFolder,
    IReadOnlyList<string> SourceFiles,
    IReadOnlyList<string> TestFiles,
    IReadOnlyList<string> SkipFolders,
    IReadOnlyList<string> BannedFolderNames,
    IReadOnlyDictionary<string, string> NameMap)
{
    public const string RelativePath = ".claude/rules/file-placement.md";

    public static PlacementRules Read(RulesFile file)
    {
        var maxTypesPerFolder = file.RequireWholeNumber("max-types-per-folder");
        var sourceFiles = file.RequireList("source-files");
        var testFiles = file.RequireList("test-files");
        var skipFolders = file.RequireList("skip-folders");
        var bannedFolderNames = file.RequireList("banned-folder-names");
        var nameMap = file.RequireMap("name-map");

        return new(maxTypesPerFolder, sourceFiles, testFiles, skipFolders, bannedFolderNames, nameMap);
    }

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

    public bool IsSkipped(string folderName) => SkipFolders.Contains(folderName, StringComparer.Ordinal);

    public bool IsBanned(string folderName) => BannedFolderNames.Contains(folderName, StringComparer.OrdinalIgnoreCase);

    private string? TestPatternOf(string fileName) =>
        TestFiles.FirstOrDefault(pattern => FileSystemName.MatchesSimpleExpression(pattern, fileName, ignoreCase: false));
}
