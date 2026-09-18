using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_folder_at_the_top_of_a_project_that_is_not_a_Slice_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Write("src/App/Reporting/Report.cs");

        Assert.Equal([("slice-folders", "src/App/Reporting")], tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_Slice_and_Shared_at_the_top_of_a_project_are_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Write("src/App/Sessions/Session.cs")
            .Write("src/App/Shared/Trigger.cs");

        Assert.Empty(tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_folder_at_the_top_of_the_front_end_that_is_not_a_Slice_is_a_breach()
    {
        using var tree = new RulesTree()
            .FrontEnd("web")
            .Write("web/src/watch/clock.ts")
            .Write("web/src/shared/format.ts")
            .Write("web/src/reporting/report.ts");

        Assert.Equal([("slice-folders", "web/src/reporting")], tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_Slice_in_the_wrong_letter_case_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/watch/Clock.cs")
            .Write("src/App/shared/Trigger.cs")
            .FrontEnd("web")
            .Write("web/src/Sessions/session.ts");

        Assert.Equal(
            [
                ("slice-folders", "src/App/shared"),
                ("slice-folders", "src/App/watch"),
                ("slice-folders", "web/src/Sessions"),
            ],
            tree.Breaches("slice-folders"));
    }

    [Fact]
    public void Shared_below_the_top_of_a_code_root_is_a_breach_in_any_letter_case()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Shared/Clock.cs")
            .FrontEnd("web")
            .Write("web/src/watch/SHARED/format.ts");

        Assert.Equal(
            [("slice-folders", "src/App/Watch/Shared"), ("slice-folders", "web/src/watch/SHARED")],
            tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_file_at_a_code_root_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Program.cs")
            .FrontEnd("web")
            .Write("web/src/router.tsx");

        Assert.Empty(tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_folder_beneath_a_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Queries/ClockQueries.cs");

        Assert.Empty(tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_folder_outside_every_code_root_is_not_a_breach()
    {
        using var tree = new RulesTree().Write("tools/Check/Timer.cs");

        Assert.Empty(tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_folder_that_is_not_a_Slice_is_one_breach_however_much_code_it_holds()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Reporting/Report.cs")
            .Write("src/App/Reporting/Totals/Total.cs");

        Assert.Equal([("slice-folders", "src/App/Reporting")], tree.Breaches("slice-folders"));
    }

    [Fact]
    public void The_Slices_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "slices", "[Reporting]")
            .Project("src/App")
            .Write("src/App/Reporting/Report.cs")
            .Write("src/App/Watch/Clock.cs");

        Assert.Equal([("slice-folders", "src/App/Watch")], tree.Breaches("slice-folders"));
    }

    [Fact]
    public void A_slice_folders_breach_names_the_folders_the_code_can_move_into()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Reporting/Report.cs");

        var breach = Assert.Single(tree.Check("slice-folders").Breaches);

        Assert.Contains("`Watch`", breach.Message);
        Assert.Contains("`Sessions`", breach.Message);
        Assert.Contains("`Shared`", breach.Message);
    }

    [Fact]
    public void The_slice_folders_check_is_not_in_the_run()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Reporting/Report.cs");

        Assert.Empty(tree.Breaches());
    }
}
