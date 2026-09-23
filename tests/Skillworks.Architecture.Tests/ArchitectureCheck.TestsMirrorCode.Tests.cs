namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_csharp_test_at_the_path_that_mirrors_its_code_file_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/Clock.cs", TypeIn("App", "Clock"))
            .Write("src/App/Shared/Ledger/Locators/LedgerLocator.cs", TypeIn("App.Shared.Ledger.Locators", "LedgerLocator"))
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Clock.Tests.cs", TypeIn("App.Tests", "ClockTests"))
            .Write("tests/App.Tests/Shared/Ledger/Locators/LedgerLocator.Tests.cs", TypeIn("App.Tests.Shared.Ledger.Locators", "LedgerLocatorTests"))
            .Write("tests/App.Tests/Shared/Ledger/Locators/LedgerLocator.Cache.Tests.cs", TypeIn("App.Tests.Shared.Ledger.Locators", "LedgerLocatorTests"));

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Shared/Timers/Clock.cs", "App.Shared.Timers", "Clock")]
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
            .Write("src/App/Shared/Timers/Clock.cs", TypeIn("App.Shared.Timers", "Clock"))
            .Write("tests/App.Tests/App.Tests.csproj", ProjectFile)
            .Write("tests/App.Tests/Clock.Tests.cs", TypeIn("App.Tests", "ClockTests"));

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("tests-mirror-code", "tests/App.Tests/Clock.Tests.cs"), (breach.Rule, breach.Path));
        Assert.Contains("`tests/App.Tests/Shared/Timers/Clock.Tests.cs`", breach.Message);
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
    public void A_tsx_test_is_a_breach_only_without_a_code_file_of_its_subject_beside_it()
    {
        using var tree = new RulesTree()
            .Write("web/src/clock/Clock.tsx")
            .Write("web/src/clock/Clock.test.tsx")
            .Write("web/src/clock/Alarm.test.tsx");

        Assert.Equal([("tests-mirror-code", "web/src/clock/Alarm.test.tsx")], tree.Breaches());
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
            .Write("tests/App.Tests/Shared/Hosts/AppHost.cs", TypeIn("App.Tests.Shared.Hosts", "AppHost"))
            .Write("web/src/skills/lib/fakeClock.ts");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Every_mirror_breach_speaks_of_the_code_file_a_test_mirrors()
    {
        using var tree = new RulesTree()
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/Shared/Alarms/Alarm.cs", TypeIn("App.Shared.Alarms", "Alarm"))
            .Write("src/App/Shared/Snoozes/Alarm.cs", TypeIn("App.Shared.Snoozes", "Alarm"))
            .Write("src/App/Shared/Timers/Clock.cs", TypeIn("App.Shared.Timers", "Clock"))
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

    [Fact]
    public void A_shell_test_beneath_a_test_root_that_mirrors_its_code_file_is_not_a_breach()
    {
        using var tree = ShellTree()
            .Write("scripts/spec-loop.sh", Script)
            .Write("scripts/watch/tail.sh", Script)
            .Write("tests/scripts/spec-loop.test.sh", Script)
            .Write("tests/scripts/watch/tail.test.sh", Script);

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_shell_test_beside_the_code_file_it_tests_is_not_a_breach()
    {
        using var tree = ShellTree()
            .Write("scripts/spec-loop.sh", Script)
            .Write("scripts/spec-loop.test.sh", Script);

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_shell_test_beneath_a_test_root_is_told_the_folder_its_code_file_should_sit_in()
    {
        using var tree = ShellTree()
            .Write("scripts/spec-loop.sh", Script)
            .Write("tests/scripts/watch/tail.test.sh", Script);

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("tests-mirror-code", "tests/scripts/watch/tail.test.sh"), (breach.Rule, breach.Path));
        Assert.Contains("`scripts/watch`", breach.Message);
    }

    [Fact]
    public void A_shell_test_in_a_folder_no_test_root_covers_mirrors_nothing()
    {
        using var tree = ShellTree()
            .Write("scripts/spec-loop.sh", Script)
            .Write("tests/tools/spec-loop.test.sh", Script);

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("tests-mirror-code", "tests/tools/spec-loop.test.sh"), (breach.Rule, breach.Path));
        Assert.Contains("beside", breach.Message);
    }

    [Fact]
    public void A_support_script_beneath_a_test_root_is_not_a_breach()
    {
        using var tree = ShellTree()
            .Write("scripts/spec-loop.sh", Script)
            .Write("tests/scripts/harness.sh", Script);

        Assert.Empty(tree.Breaches());
    }

    private const string Script = "#!/usr/bin/env bash\n";

    private static RulesTree ShellTree() =>
        new RulesTree()
            .Set(RulesTree.PlacementFile, "source-files", "[.cs, .ts, .tsx, .sh]")
            .Set(RulesTree.PlacementFile, "test-files", "[\"*.Tests.cs\", \"*.test.ts\", \"*.test.tsx\", \"*.test.sh\"]")
            .Set(RulesTree.PlacementFile, "test-roots", "{tests/scripts: scripts}");

    private static string TypeIn(string namespaceName, string typeName) =>
        $"namespace {namespaceName};\n\npublic sealed partial class {typeName};\n";
}
