using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    private const string TwoPatterns = "{\"*Extensions\": Extensions, \"Store*\": Stores}";

    [Theory]
    [InlineData("src/App/Stores/ActivationStore.cs")]
    [InlineData("src/App/Activations/Stores/ActivationStore.cs")]
    [InlineData("src/App/Activations/Stores/ActivationStore.Async.cs")]
    public void A_name_that_matches_a_pattern_is_not_a_breach_in_that_patterns_folder(string file)
    {
        using var tree = new RulesTree().Write(file);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Activations/ActivationStore.cs")]
    [InlineData("src/App/Stores/Activations/ActivationStore.cs")]
    [InlineData("src/App/stores/ActivationStore.cs")]
    [InlineData("tests/App.Tests/Activations/FakeActivationStore.cs")]
    [InlineData("web/src/activations/lib/activationStore.ts")]
    public void A_name_that_matches_a_pattern_is_a_breach_outside_that_patterns_folder(string file)
    {
        using var tree = new RulesTree().Write(file);

        Assert.Equal([("name-map", file)], tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Extensions/StoreLoggerExtensions.cs")]
    [InlineData("src/App/Stores/StoreLoggerExtensions.cs")]
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
            .Write("src/App/Logging/StoreLoggerExtensions.cs");

        Assert.Equal([("name-map", "src/App/Logging/StoreLoggerExtensions.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Activations/Clock.cs")]
    [InlineData("src/App/Stores/Clock.cs")]
    [InlineData("src/App/Activations/ActivationSTORE.cs")]
    [InlineData("src/App/Activations/StoreFront.cs")]
    public void A_name_that_matches_no_pattern_is_not_a_breach_anywhere(string file)
    {
        using var tree = new RulesTree().Write(file);

        Assert.Empty(tree.Breaches());
    }
}
