using Skillworks.Architecture.Placement.CSharp;

namespace Skillworks.Architecture.Placement;

internal static class TestsMirrorCode
{
    public const string Rule = "tests-mirror-code";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules)
    {
        var tests = sourceFiles.Where(file => rules.IsTestFile(Path.GetFileName(file))).ToList();

        var codeFiles = sourceFiles
            .Except(tests)
            .Select(file => (Folder: SourceTree.FolderOf(file), Subject: rules.SubjectOf(file), IsCSharp: CSharpFile.IsCSharp(file)))
            .ToHashSet();

        var projects = CSharpProject.AboveEach(root, sourceFiles.Where(CSharpFile.IsCSharp).Select(SourceTree.FolderOf));

        foreach (var test in tests)
        {
            var folder = SourceTree.FolderOf(test);
            var fileName = Path.GetFileName(test);
            var subject = rules.NameOf(fileName).Subject;

            if (!CSharpFile.IsCSharp(test))
            {
                if (!codeFiles.Contains((folder, subject, IsCSharp: false)))
                    yield return new Breach(Rule, test, $"Move the test beside the `{subject}` code file it tests, or delete it.");

                continue;
            }

            if (projects[folder] is not { TestedProjectName: { } codeProjectName } testProject)
                continue;

            var codeProject = projects.Values
                .OfType<CSharpProject>()
                .Where(project => project.Name == codeProjectName)
                .MinBy(project => project.Folder, StringComparer.Ordinal);

            if (codeProject is null)
            {
                yield return new Breach(
                    Rule,
                    test,
                    $"Put the test in the `.Tests` project of the project that holds the code file it tests, or delete it: no project `{codeProjectName}` holds code files.");

                continue;
            }

            var mirror = testProject.FolderMirroredIn(codeProject, folder);
            if (codeFiles.Contains((mirror, subject, IsCSharp: true)))
                continue;

            var codeFolders = codeFiles
                .Where(entry => entry.Subject == subject && entry.IsCSharp && projects.GetValueOrDefault(entry.Folder) == codeProject)
                .Select(entry => entry.Folder)
                .ToList();

            yield return new Breach(
                Rule,
                test,
                codeFolders switch
                {
                    [] => $"No `{subject}` code file sits at `{mirror}`. Move the test to mirror the code file it tests, or delete it.",
                    [var only] => $"Move the test to `{codeProject.FolderMirroredIn(testProject, only)}/{fileName}`, which mirrors the `{subject}` code file in `{only}`.",
                    _ => $"Move the test to the path that mirrors the `{subject}` code file it tests in `{codeProject.Folder}`.",
                });
        }
    }
}
