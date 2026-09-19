using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_folder_inside_a_front_end_Slice_that_is_not_a_Concern_is_a_breach()
    {
        using var tree = new RulesTree()
            .FrontEnd("web")
            .Write("web/src/watch/components/clock.tsx")
            .Write("web/src/watch/dials/dial.tsx");

        Assert.Equal([("concern-folders", "web/src/watch/dials")], tree.Breaches());
    }

    [Fact]
    public void Every_Concern_inside_a_front_end_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .FrontEnd("web")
            .Write("web/src/watch/api/clock.ts")
            .Write("web/src/watch/components/clock.tsx")
            .Write("web/src/watch/lib/format.ts")
            .Write("web/src/watch/routes/watch.tsx");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_file_at_the_top_of_a_front_end_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree().FrontEnd("web").Write("web/src/watch/clock.ts");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_folder_beneath_a_Concern_is_not_a_breach()
    {
        using var tree = new RulesTree().FrontEnd("web").Write("web/src/watch/components/dials/dial.tsx");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_C_sharp_folder_inside_a_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Dials/Dial.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_folder_inside_the_front_end_shared_folder_is_not_a_breach()
    {
        using var tree = new RulesTree().FrontEnd("web").Write("web/src/shared/http/get.ts");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_folder_inside_a_front_end_folder_that_is_no_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree().FrontEnd("web").Write("web/src/reporting/dials/report.ts");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void The_Concerns_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "concerns", "[dials]")
            .FrontEnd("web")
            .Write("web/src/watch/dials/dial.tsx")
            .Write("web/src/watch/components/clock.tsx");

        Assert.Equal([("concern-folders", "web/src/watch/components")], tree.Breaches());
    }

    [Fact]
    public void A_concern_folders_breach_names_the_Concerns_the_code_can_move_into()
    {
        using var tree = new RulesTree().FrontEnd("web").Write("web/src/watch/dials/dial.tsx");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Contains("`api`", breach.Message);
        Assert.Contains("`components`", breach.Message);
        Assert.Contains("`lib`", breach.Message);
        Assert.Contains("`routes`", breach.Message);
    }

    [Fact]
    public void A_breach_with_no_Concern_to_name_still_says_so()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "concerns", "[]")
            .FrontEnd("web")
            .Write("web/src/watch/dials/dial.tsx");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Contains("no folder the rules name", breach.Message);
    }

    [Fact]
    public void A_stray_Shared_inside_a_Slice_is_a_breach()
    {
        using var tree = new RulesTree().FrontEnd("web").Write("web/src/watch/shared/format.ts");

        Assert.Equal([("concern-folders", "web/src/watch/shared")], tree.Breaches());
    }
}
