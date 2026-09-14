using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void Only_source_files_are_scanned()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs")
            .Write("src/App/App.csproj")
            .Write("web/src/main.tsx")
            .Write("web/src/format.ts")
            .Write("web/utils/build.js")
            .Write("docs/shared/notes.md");

        var result = tree.Check();

        Assert.Empty(result.Breaches);
        Assert.Equal(3, result.SourceFilesScanned);
    }

    [Fact]
    public void The_source_files_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "source-files", "[.py]")
            .Write("tools/utils/release.py")
            .Write("src/App/utils/Clock.cs");

        var result = tree.Check();

        Assert.Equal(
            [("banned-folder-names", "tools/utils")],
            result.Breaches.Select(breach => (breach.Rule, breach.Path)));
        Assert.Equal(1, result.SourceFilesScanned);
    }
}
