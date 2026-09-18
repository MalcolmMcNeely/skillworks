using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_Slice_at_the_top_of_every_code_root_that_holds_its_code_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Project("src/Api")
            .Write("src/Api/Watch/ClockEndpoints.cs")
            .FrontEnd("web")
            .Write("web/src/watch/clock.ts");

        Assert.Empty(tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void A_Slice_below_the_top_of_a_code_root_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/Api")
            .Write("src/Api/Endpoints/Watch/ClockEndpoints.cs")
            .FrontEnd("web")
            .Write("web/src/routes/watch/clock.ts");

        Assert.Equal(
            [("slice-names-match", "src/Api/Endpoints/Watch"), ("slice-names-match", "web/src/routes/watch")],
            tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void A_Slice_under_another_letter_case_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/Api")
            .Write("src/Api/Endpoints/watch/ClockEndpoints.cs")
            .FrontEnd("web")
            .Write("web/src/routes/Sessions/panel.ts");

        Assert.Equal(
            [("slice-names-match", "src/Api/Endpoints/watch"), ("slice-names-match", "web/src/routes/Sessions")],
            tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void A_Slice_at_the_top_in_another_letter_case_is_left_to_the_slice_folders_rule()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/watch/Clock.cs");

        Assert.Equal(
            [("slice-folders", "src/App/watch")],
            tree.Breaches("slice-folders", "slice-names-match"));
    }

    [Fact]
    public void A_code_root_that_holds_none_of_a_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Project("src/Api")
            .Write("src/Api/Shared/Health.cs");

        Assert.Empty(tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void A_Slice_folder_inside_another_Slice_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Sessions/Panel.cs");

        Assert.Equal([("slice-names-match", "src/App/Watch/Sessions")], tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void A_folder_that_names_no_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Reporting/Totals/Total.cs");

        Assert.Empty(tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void A_Slice_folder_outside_every_code_root_is_not_a_breach()
    {
        using var tree = new RulesTree().Write("tools/Check/Watch/Clock.cs");

        Assert.Empty(tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void The_Slices_matched_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "slices", "[Reporting]")
            .Project("src/App")
            .Write("src/App/Api/Reporting/Report.cs")
            .Write("src/App/Api/Watch/Clock.cs");

        Assert.Equal([("slice-names-match", "src/App/Api/Reporting")], tree.Breaches("slice-names-match"));
    }

    [Fact]
    public void A_slice_names_match_breach_names_the_Slice_where_it_goes_and_what_to_do()
    {
        using var tree = new RulesTree()
            .Project("src/Api")
            .Write("src/Api/Endpoints/Watch/ClockEndpoints.cs");

        var breach = Assert.Single(tree.Check("slice-names-match").Breaches);

        Assert.Contains("`Watch`", breach.Message);
        Assert.Contains("`src/Api/Watch`", breach.Message);
        Assert.Contains("Move", breach.Message);
    }

    [Fact]
    public void The_slice_names_match_check_is_not_in_the_run()
    {
        using var tree = new RulesTree()
            .Project("src/Api")
            .Write("src/Api/Endpoints/Watch/ClockEndpoints.cs");

        Assert.Empty(tree.Breaches());
    }
}
