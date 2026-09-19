namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void Every_Slice_rule_passes_over_a_context_that_declares_no_Slices()
    {
        using var tree = new RulesTree()
            .Project("tools/Check/Rules")
            .Write("tools/Check/Rules/Watch/Clock.cs")
            .Write("tools/Check/Rules/Reporting/Watch/Total.cs")
            .Reads("tools/Check/Rules/Shared/Gadgets/Timer.cs", "Rules.Watch")
            .FrontEnd("tools/Check/web")
            .Write("tools/Check/web/src/watch/pages/clock.ts");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_context_that_declares_Slices_is_judged_by_them()
    {
        using var tree = new RulesTree()
            .Slices("check", true)
            .Project("tools/Check/Rules")
            .Write("tools/Check/Rules/Reporting/Report.cs");

        Assert.Equal([("slice-folders", "tools/Check/Rules/Reporting")], tree.Breaches());
    }

    [Fact]
    public void A_context_that_stops_declaring_Slices_stops_being_judged_by_them()
    {
        using var tree = new RulesTree()
            .Slices("app", false)
            .Project("src/App")
            .Write("src/App/Reporting/Report.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Code_no_context_claims_is_judged_by_no_Slice_rule()
    {
        using var tree = new RulesTree()
            .Project("outside/App")
            .Write("outside/App/Reporting/Report.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void The_files_a_Slice_rule_passes_over_are_still_counted_as_scanned()
    {
        using var tree = new RulesTree()
            .Project("tools/Check/Rules")
            .Write("tools/Check/Rules/Reporting/Report.cs");

        Assert.Equal(1, tree.Check().SourceFilesScanned);
    }
}
