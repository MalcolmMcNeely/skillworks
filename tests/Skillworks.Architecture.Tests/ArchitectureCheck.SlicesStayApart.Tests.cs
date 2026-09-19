using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_code_file_in_a_Slice_that_reads_another_Slice_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Sessions/Session.cs")
            .Reads("src/App/Watch/Clock.cs", "App.Sessions");

        Assert.Equal([("slices-stay-apart", "src/App/Watch/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_code_file_that_reads_a_folder_of_its_own_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Queries/ClockQueries.cs")
            .Reads("src/App/Watch/Clock.cs", "App.Watch.Queries");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_code_file_that_reads_Shared_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Shared/Trigger.cs")
            .Reads("src/App/Watch/Clock.cs", "App.Shared");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_code_file_that_reads_the_same_Slice_in_another_project_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Project("src/Api")
            .Reads("src/Api/Watch/ClockEndpoints.cs", "App.Watch");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_test_file_that_reads_another_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Write("src/App/Sessions/Session.cs")
            .Project("tests/App.Tests")
            .Reads("tests/App.Tests/Watch/Clock.Tests.cs", "App.Sessions");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_code_file_in_Shared_that_reads_a_Slice_is_no_breach_of_this_rule()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Reads("src/App/Shared/Trigger.cs", "App.Watch");

        Assert.DoesNotContain(tree.Breaches(), breach => breach.Rule == "slices-stay-apart");
    }

    [Fact]
    public void A_code_file_at_a_code_root_that_reads_a_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Sessions/Session.cs")
            .Reads("src/App/Program.cs", "App.Sessions");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_Slice_read_through_a_static_or_an_alias_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Sessions/Session.cs")
            .Write(
                "src/App/Watch/Clock.cs",
                "using static App.Sessions.Session;\n\nnamespace App.Watch;\n\npublic sealed partial class Clock;\n")
            .Write(
                "src/App/Watch/Dial.cs",
                "using Held = App.Sessions;\n\nnamespace App.Watch;\n\npublic sealed partial class Dial;\n");

        Assert.Equal(
            [("slices-stay-apart", "src/App/Watch/Clock.cs"), ("slices-stay-apart", "src/App/Watch/Dial.cs")],
            tree.Breaches());
    }

    [Fact]
    public void A_code_file_that_reads_two_Slices_is_one_breach()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "slices", "[Watch, Sessions, Author]")
            .Project("src/App")
            .Write("src/App/Sessions/Session.cs")
            .Write("src/App/Author/Draft.cs")
            .Reads("src/App/Watch/Clock.cs", "App.Sessions", "App.Author");

        Assert.Equal([("slices-stay-apart", "src/App/Watch/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void The_Slices_held_apart_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "slices", "[Watch, Reporting]")
            .Project("src/App")
            .Write("src/App/Reporting/Report.cs")
            .Reads("src/App/Watch/Clock.cs", "App.Reporting");

        Assert.Equal([("slices-stay-apart", "src/App/Watch/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_slices_stay_apart_breach_names_the_Slice_read_and_what_to_do()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Sessions/Session.cs")
            .Reads("src/App/Watch/Clock.cs", "App.Sessions");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Contains("`Watch`", breach.Message);
        Assert.Contains("`App.Sessions`", breach.Message);
        Assert.Contains("`Shared`", breach.Message);
    }
}
