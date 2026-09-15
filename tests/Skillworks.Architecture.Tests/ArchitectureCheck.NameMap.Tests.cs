using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    private const string TwoPatterns = "{\"*Extensions\": Extensions, \"Query*\": Queries}";

    [Theory]
    [InlineData("src/App/Queries/ActivationQueries.cs")]
    [InlineData("src/App/Activations/Queries/ActivationQueries.cs")]
    [InlineData("src/App/Activations/Queries/ActivationQueries.Async.cs")]
    public void A_name_that_matches_a_pattern_is_not_a_breach_in_that_patterns_folder(string file)
    {
        using var tree = new RulesTree().Write(file);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Activations/ActivationQueries.cs")]
    [InlineData("src/App/Queries/Activations/ActivationQueries.cs")]
    [InlineData("src/App/queries/ActivationQueries.cs")]
    [InlineData("tests/App.Tests/Activations/FakeActivationQueries.cs")]
    [InlineData("web/src/activations/lib/activationQueries.ts")]
    public void A_name_that_matches_a_pattern_is_a_breach_outside_that_patterns_folder(string file)
    {
        using var tree = new RulesTree().Write(file);

        Assert.Equal([("name-map", file)], tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Extensions/QueryLoggerExtensions.cs")]
    [InlineData("src/App/Queries/QueryLoggerExtensions.cs")]
    public void A_name_that_matches_two_patterns_is_not_a_breach_in_either_folder(string file)
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "name-map", TwoPatterns)
            .Write(file);

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_name_that_matches_two_patterns_is_a_breach_in_a_third_folder()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "name-map", TwoPatterns)
            .Write("src/App/Logging/QueryLoggerExtensions.cs");

        Assert.Equal([("name-map", "src/App/Logging/QueryLoggerExtensions.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Activations/Clock.cs")]
    [InlineData("src/App/Queries/Clock.cs")]
    [InlineData("src/App/Activations/ActivationQUERIES.cs")]
    [InlineData("src/App/Activations/QueriesPanel.cs")]
    public void A_name_that_matches_no_pattern_is_not_a_breach_anywhere(string file)
    {
        using var tree = new RulesTree().Write(file);

        Assert.Empty(tree.Breaches());
    }
}
