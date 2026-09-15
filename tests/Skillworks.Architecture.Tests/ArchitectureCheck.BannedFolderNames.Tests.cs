using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_folder_with_a_banned_name_is_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/utils/Clock.cs")
            .Write("src/App/Catalogue/CatalogueLocator.cs");

        Assert.Equal([("banned-folder-names", "src/App/utils")], tree.Breaches());
    }

    [Fact]
    public void A_banned_name_is_a_breach_in_any_letter_case()
    {
        using var tree = new RulesTree()
            .Write("src/App/Helpers/Clock.cs")
            .Write("web/src/SHARED/format.ts");

        Assert.Equal(
            [("banned-folder-names", "src/App/Helpers"), ("banned-folder-names", "web/src/SHARED")],
            tree.Breaches());
    }

    [Fact]
    public void A_banned_folder_is_one_breach_however_much_code_it_holds()
    {
        using var tree = new RulesTree()
            .Write("src/App/misc/Clock.cs")
            .Write("src/App/misc/Retry.cs")
            .Write("src/App/misc/Text/Slug.cs");

        Assert.Equal([("banned-folder-names", "src/App/misc")], tree.Breaches());
    }

    [Fact]
    public void A_support_file_in_a_folder_with_a_banned_name_is_a_breach()
    {
        using var tree = new RulesTree()
            .Write("tests/App.Tests/Clock.Tests.cs")
            .Write("tests/App.Tests/Helpers/AppHost.cs")
            .Write("web/src/clock/clock.ts")
            .Write("web/src/clock/clock.test.ts")
            .Write("web/src/clock/helpers/clockHost.tsx");

        Assert.Equal(
            [("banned-folder-names", "tests/App.Tests/Helpers"), ("banned-folder-names", "web/src/clock/helpers")],
            tree.Breaches());
    }

    [Fact]
    public void A_folder_whose_name_only_contains_a_banned_name_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/SharedLinks/SharedLink.cs")
            .Write("src/App/Commonwealth/Realm.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void The_banned_names_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "banned-folder-names", "[vendor]")
            .Write("src/App/vendor/Clock.cs")
            .Write("src/App/utils/Retry.cs");

        Assert.Equal([("banned-folder-names", "src/App/vendor")], tree.Breaches());
    }
}
