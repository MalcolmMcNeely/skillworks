namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_code_file_in_Shared_that_reads_a_Slice_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Reads("src/App/Shared/Trigger.cs", "App.Watch");

        Assert.Equal([("shared-stays-below", "src/App/Shared/Trigger.cs")], tree.Breaches("shared-stays-below"));
    }

    [Fact]
    public void A_code_file_in_Shared_that_reads_a_Slice_of_another_project_is_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Reads("src/App/Shared/Trigger.cs", "Api.Sessions")
            .Project("src/Api")
            .Write("src/Api/Sessions/SessionEndpoints.cs");

        Assert.Equal([("shared-stays-below", "src/App/Shared/Trigger.cs")], tree.Breaches("shared-stays-below"));
    }

    [Fact]
    public void A_code_file_in_Shared_that_reads_Shared_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Shared/Health/Health.cs")
            .Reads("src/App/Shared/Trigger.cs", "App.Shared.Health");

        Assert.Empty(tree.Breaches("shared-stays-below"));
    }

    [Fact]
    public void A_test_file_in_Shared_that_reads_a_Slice_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Write("src/App/Shared/Trigger.cs")
            .Project("tests/App.Tests")
            .Reads("tests/App.Tests/Shared/Trigger.Tests.cs", "App.Watch");

        Assert.Empty(tree.Breaches("shared-stays-below"));
    }

    [Fact]
    public void A_code_file_in_a_Slice_that_reads_another_Slice_is_no_breach_of_this_rule()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Sessions/Session.cs")
            .Reads("src/App/Watch/Clock.cs", "App.Sessions");

        Assert.Empty(tree.Breaches("shared-stays-below"));
    }

    [Fact]
    public void A_code_file_in_Shared_that_reads_two_Slices_is_one_breach()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Write("src/App/Sessions/Session.cs")
            .Reads("src/App/Shared/Trigger.cs", "App.Watch", "App.Sessions");

        Assert.Equal([("shared-stays-below", "src/App/Shared/Trigger.cs")], tree.Breaches("shared-stays-below"));
    }

    [Fact]
    public void A_shared_stays_below_breach_names_the_Slice_read_and_what_to_do()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Reads("src/App/Shared/Trigger.cs", "App.Watch");

        var breach = Assert.Single(tree.Check("shared-stays-below").Breaches);

        Assert.Contains("`Shared`", breach.Message);
        Assert.Contains("`App.Watch`", breach.Message);
    }

    [Fact]
    public void The_shared_stays_below_check_is_not_in_the_run()
    {
        using var tree = new RulesTree()
            .Project("src/App")
            .Write("src/App/Watch/Clock.cs")
            .Reads("src/App/Shared/Trigger.cs", "App.Watch");

        Assert.Empty(tree.Breaches());
    }
}
