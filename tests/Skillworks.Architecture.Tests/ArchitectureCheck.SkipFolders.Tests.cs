using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_skip_folder_is_not_scanned()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs")
            .Write("src/App/bin/shared/Clock.cs")
            .Write("src/App/Migrations/utils/Initial.cs")
            .Write("web/node_modules/left-pad/utils/index.ts");

        var result = tree.Check();

        Assert.Empty(result.Breaches);
        Assert.Equal(1, result.SourceFilesScanned);
    }

    [Fact]
    public void The_skip_folders_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "skip-folders", "[vendor]")
            .Write("vendor/utils/Clock.cs")
            .Write("src/App/bin/utils/Clock.cs");

        Assert.Equal([("banned-folder-names", "src/App/bin/utils")], tree.Breaches());
    }
}
