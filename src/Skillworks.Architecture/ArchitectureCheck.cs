using Skillworks.Architecture.Comments;
using Skillworks.Architecture.Contexts;
using Skillworks.Architecture.Placement;
using Skillworks.Architecture.Placement.Slices;
using Skillworks.Architecture.Words;

namespace Skillworks.Architecture;

public static class ArchitectureCheck
{
    public static CheckResult Run(string root, params string[] alsoRun)
    {
        var rules = Rules.Read(root);
        if (rules.Breaches.Count > 0)
            return new CheckResult(rules.Breaches, SourceFilesScanned: 0);

        var sourceFiles = SourceTree.Find(root, rules.Placement);

        // Slices are one context's way of laying code out, so a context laid out another way answers to none of them.
        var sliceFiles = sourceFiles.Where(rules.Contexts.DeclaresSlices).ToList();

        // A rule is proved before it joins the run, so a caller can ask for one the tree cannot pass yet.
        IEnumerable<Breach> WhenAskedFor(string rule, Func<IEnumerable<Breach>> check) =>
            alsoRun.Contains(rule, StringComparer.Ordinal) ? check() : [];

        return new CheckResult(
            [
                .. ContextMap.Check(root, rules.Contexts),
                .. MaxTypesPerFolder.Check(sourceFiles, rules.Placement),
                .. NameMap.Check(sourceFiles, rules.Placement),
                .. BannedFolderNames.Check(sourceFiles, rules.Placement),
                .. OneTypePerFile.Check(root, sourceFiles, rules.Placement),
                .. NamespaceFollowsFolder.Check(root, sourceFiles),
                .. TestsMirrorCode.Check(root, sourceFiles, rules.Placement),
                .. DocComments.Check(root, sourceFiles, rules.Placement, rules.Comments),
                .. BannedWords.Check(root, sourceFiles, rules.Words, rules.Contexts),
                .. SliceFolders.Check(root, sliceFiles, rules.Placement),
                .. ConcernFolders.Check(root, sliceFiles, rules.Placement),
                .. SlicesStayApart.Check(root, sliceFiles, rules.Placement),
                .. SharedStaysBelow.Check(root, sliceFiles, rules.Placement),
                .. WhenAskedFor(
                    SharedNamesAWord.Rule,
                    () => SharedNamesAWord.Check(root, sliceFiles, rules.Placement, rules.Contexts)),
                .. SliceNamesMatch.Check(root, sliceFiles, rules.Placement),
            ],
            sourceFiles.Count);
    }
}
