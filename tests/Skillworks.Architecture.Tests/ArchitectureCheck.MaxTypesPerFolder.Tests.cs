using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Fact]
    public void A_folder_over_the_limit_is_a_breach()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "max-types-per-folder", "2")
            .Write("src/App/Alarm.cs")
            .Write("src/App/Clock.cs")
            .Write("src/App/Timer.cs")
            .Write("src/App/Timers/Lap.cs")
            .Write("src/App/Timers/Stopwatch.cs");

        Assert.Equal([("max-types-per-folder", "src/App")], tree.Breaches());
    }

    [Fact]
    public void Aspect_files_and_the_tests_beside_a_code_file_take_one_place()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "max-types-per-folder", "2")
            .Write("src/App/BlobRepository.cs")
            .Write("src/App/BlobRepository.Async.cs")
            .Write("src/App/Clock.cs")
            .Write("web/src/clock/format.ts")
            .Write("web/src/clock/format.test.ts")
            .Write("web/src/clock/format.dates.test.ts")
            .Write("web/src/clock/Clock.tsx");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_test_with_no_code_file_beside_it_counts_as_one()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "max-types-per-folder", "2")
            .Write("tests/App.Tests/Alarm.Tests.cs")
            .Write("tests/App.Tests/Clock.Tests.cs")
            .Write("tests/App.Tests/Timer.Tests.cs");

        Assert.Equal([("max-types-per-folder", "tests/App.Tests")], tree.Breaches());
    }

    [Fact]
    public void Tests_of_one_subject_with_no_code_file_beside_them_take_one_place()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "max-types-per-folder", "2")
            .Write("tests/App.Tests/Clock.Tests.cs")
            .Write("tests/App.Tests/Clock.Lease.Tests.cs")
            .Write("tests/App.Tests/Timer.Tests.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Subfolders_do_not_count_toward_a_folders_size()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "max-types-per-folder", "2")
            .Write("src/App/Clock.cs")
            .Write("src/App/Timer.cs")
            .Write("src/App/Alarms/Alarm.cs")
            .Write("src/App/Snoozes/Snooze.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Files_that_are_not_source_files_do_not_count_toward_a_folders_size()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "max-types-per-folder", "2")
            .Write("src/App/Clock.cs", "namespace App;\n\npublic sealed class Clock;\n")
            .Write("src/App/Timer.cs", "namespace App;\n\npublic sealed class Timer;\n")
            .Write("src/App/App.csproj", ProjectFile)
            .Write("src/App/appsettings.json")
            .Write("src/App/README.md");

        Assert.Empty(tree.Breaches());
    }
}
