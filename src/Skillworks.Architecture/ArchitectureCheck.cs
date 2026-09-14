using Skillworks.Architecture.Placement;

namespace Skillworks.Architecture;

public static class ArchitectureCheck
{
    public static CheckResult Run(string root)
    {
        var rules = Rules.Read(root);
        if (rules.Breaches.Count > 0)
            return new CheckResult(rules.Breaches, SourceFilesScanned: 0);

        var sourceFiles = SourceTree.Find(root, rules.Placement);

        return new CheckResult([.. BannedFolderNames.Check(sourceFiles, rules.Placement)], sourceFiles.Count);
    }
}
