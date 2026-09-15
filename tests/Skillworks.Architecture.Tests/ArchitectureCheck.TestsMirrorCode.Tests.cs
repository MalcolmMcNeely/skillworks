namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_csharp_test_at_the_path_that_mirrors_its_code_file_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/Clock.cs", TypeIn("App", "Clock"))
            .Write("src/App/Catalogue/Locators/CatalogueLocator.cs", TypeIn("App.Catalogue.Locators", "CatalogueLocator"))
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Clock.Tests.cs", TypeIn("App.Tests", "ClockTests"))
            .Write("tests/App.Tests/Catalogue/Locators/CatalogueLocator.Tests.cs", TypeIn("App.Tests.Catalogue.Locators", "CatalogueLocatorTests"))
            .Write("tests/App.Tests/Catalogue/Locators/CatalogueLocator.Cache.Tests.cs", TypeIn("App.Tests.Catalogue.Locators", "CatalogueLocatorTests"));

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Timers/Clock.cs", "App.Timers", "Clock")]
    [InlineData("src/App/Timer.cs", "App", "Timer")]
    [InlineData("src/Tools/Clock.cs", "Tools", "Clock")]
    public void A_csharp_test_with_no_code_file_at_the_mirrored_path_is_a_breach(string codeFile, string namespaceName, string typeName)
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write(codeFile, TypeIn(namespaceName, typeName))
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Clock.Tests.cs", TypeIn("App.Tests", "ClockTests"));

        Assert.Equal([("tests-mirror-code", "tests/App.Tests/Clock.Tests.cs")], tree.Breaches());
    }

    [Fact]
    public void A_csharp_test_whose_code_file_sits_in_another_folder_is_told_where_to_move()
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/Timers/Clock.cs", TypeIn("App.Timers", "Clock"))
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Clock.Tests.cs", TypeIn("App.Tests", "ClockTests"));

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Contains("`tests/App.Tests/Timers/Clock.Tests.cs`", breach.Message);
    }

    [Theory]
    [InlineData("tests/App.Specs/App.Specs.csproj")]
    [InlineData(null)]
    public void A_csharp_test_outside_a_Tests_project_has_no_code_file_to_mirror(string? projectFile)
    {
        using var tree = new RulesTree().Write("tests/App.Specs/Clock.Tests.cs", TypeIn("App.Specs", "ClockTests"));
        if (projectFile is not null)
            tree.Write(projectFile, ProjectFile);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("web/src/skills/lib/format.ts")]
    [InlineData("web/src/skills/lib/format.tsx")]
    public void A_front_end_test_beside_a_code_file_of_its_subject_is_not_a_breach(string codeFile)
    {
        using var tree = new RulesTree()
            .Write(codeFile)
            .Write("web/src/skills/lib/format.test.ts")
            .Write("web/src/skills/lib/format.dates.test.ts");

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("web/src/skills/format.ts")]
    [InlineData("web/src/skills/lib/formats.ts")]
    public void A_front_end_test_with_no_code_file_of_its_subject_beside_it_is_a_breach(string codeFile)
    {
        using var tree = new RulesTree()
            .Write(codeFile)
            .Write("web/src/skills/lib/format.test.ts");

        Assert.Equal([("tests-mirror-code", "web/src/skills/lib/format.test.ts")], tree.Breaches());
    }

    [Fact]
    public void A_code_file_in_the_other_language_is_not_the_code_file_a_test_mirrors()
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/Timer.cs", TypeIn("App", "Timer"))
            .Write("src/App/Clock.ts")
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Clock.Tests.cs", TypeIn("App.Tests", "ClockTests"))
            .Write("web/src/skills/lib/format.cs")
            .Write("web/src/skills/lib/format.test.ts");

        Assert.Equal(
            [("tests-mirror-code", "tests/App.Tests/Clock.Tests.cs"), ("tests-mirror-code", "web/src/skills/lib/format.test.ts")],
            tree.Breaches());
    }

    [Fact]
    public void A_support_file_with_no_code_file_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/Clock.cs", TypeIn("App", "Clock"))
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Hosts/AppHost.cs", TypeIn("App.Tests.Hosts", "AppHost"))
            .Write("web/src/skills/lib/fakeClock.ts");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Every_mirror_breach_speaks_of_the_code_file_a_test_mirrors()
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/Alarms/Alarm.cs", TypeIn("App.Alarms", "Alarm"))
            .Write("src/App/Snoozes/Alarm.cs", TypeIn("App.Snoozes", "Alarm"))
            .Write("src/App/Timers/Clock.cs", TypeIn("App.Timers", "Clock"))
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Alarm.Tests.cs", TypeIn("App.Tests", "AlarmTests"))
            .Write("tests/App.Tests/Clock.Tests.cs", TypeIn("App.Tests", "ClockTests"))
            .Write("tests/App.Tests/Timer.Tests.cs", TypeIn("App.Tests", "TimerTests"))
            .Write("tests/Tools.Tests/Tools.Tests.csproj", ProjectFile)
            .Write("tests/Tools.Tests/Lathe.Tests.cs", TypeIn("Tools.Tests", "LatheTests"))
            .Write("web/src/skills/lib/format.test.ts");

        var breaches = tree.Check().Breaches;

        Assert.Equal(
            [
                ("tests-mirror-code", "tests/App.Tests/Alarm.Tests.cs"),
                ("tests-mirror-code", "tests/App.Tests/Clock.Tests.cs"),
                ("tests-mirror-code", "tests/App.Tests/Timer.Tests.cs"),
                ("tests-mirror-code", "tests/Tools.Tests/Lathe.Tests.cs"),
                ("tests-mirror-code", "web/src/skills/lib/format.test.ts"),
            ],
            breaches.Select(breach => (breach.Rule, breach.Path)));
        Assert.All(breaches, breach => Assert.Contains("code file", breach.Message));
    }

    private static string TypeIn(string namespaceName, string typeName) =>
        $"namespace {namespaceName};\n\npublic sealed partial class {typeName};\n";
}
