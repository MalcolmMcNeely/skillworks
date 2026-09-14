using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Theory]
    [InlineData("namespace App;\n\npublic sealed class Clock;\n\npublic sealed record Tick(DateTimeOffset At);\n")]
    [InlineData("namespace App;\n\npublic sealed class Clock;\n\npublic sealed class Clock<TZone>;\n")]
    [InlineData("namespace App\n{\n    public sealed class Clock;\n}\n\nnamespace App.Legacy\n{\n    public sealed class Clock;\n}\n")]
    public void A_second_top_level_type_is_a_breach(string content)
    {
        using var tree = new RulesTree().Write("src/App/Clock.cs", content);

        Assert.Equal([("one-type-per-file", "src/App/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_private_nested_type_and_a_file_local_type_are_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", """
                namespace App;

                public sealed class Clock
                {
                    private sealed record Tick(DateTimeOffset At);

                    struct Hand
                    {
                        enum Kind { Hour, Minute }
                    }
                }

                file static class Ticks;
                """);

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_public_type_nested_in_a_private_type_is_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", """
                namespace App;

                public sealed class Clock
                {
                    private struct Hand
                    {
                        public enum Kind { Hour, Minute }
                    }
                }
                """);

        Assert.Equal([("one-type-per-file", "src/App/Clock.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("public")]
    [InlineData("internal")]
    [InlineData("protected")]
    [InlineData("private protected")]
    public void A_nested_type_seen_outside_its_type_is_a_breach(string access)
    {
        using var tree = new RulesTree()
            .Write("src/App/Clock.cs", $$"""
                namespace App;

                public sealed class Clock
                {
                    {{access}} sealed record Tick(DateTimeOffset At);
                }
                """);

        Assert.Equal([("one-type-per-file", "src/App/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_nested_type_in_an_interface_is_a_breach_with_no_access_word()
    {
        using var tree = new RulesTree()
            .Write("src/App/IClock.cs", """
                namespace App;

                public interface IClock
                {
                    record Tick(DateTimeOffset At);
                }
                """);

        Assert.Equal([("one-type-per-file", "src/App/IClock.cs")], tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/Timer.cs", "public sealed class Clock;")]
    [InlineData("src/App/Clock.cs", "public delegate DateTimeOffset Now();")]
    [InlineData("src/App/Clock.cs", "file sealed class Clock;")]
    [InlineData("src/App/Clock.cs", "")]
    public void A_file_that_does_not_hold_a_type_named_for_it_is_a_breach(string file, string type)
    {
        using var tree = new RulesTree().Write(file, $"namespace App;\n\n{type}\n");

        Assert.Equal([("one-type-per-file", file)], tree.Breaches());
    }

    [Theory]
    [InlineData("public sealed class Clock;")]
    [InlineData("public enum Clock { Hour, Minute }")]
    [InlineData("public interface Clock;")]
    [InlineData("public delegate DateTimeOffset Clock();")]
    public void A_file_that_holds_a_type_named_for_it_is_not_a_breach(string type)
    {
        using var tree = new RulesTree().Write("src/App/Clock.cs", $"namespace App;\n\n{type}\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void Aspect_files_that_hold_parts_of_the_type_are_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/BlobRepository.cs", "namespace App;\n\npublic sealed partial class BlobRepository;\n")
            .Write("src/App/BlobRepository.Async.cs", "namespace App;\n\npublic sealed partial class BlobRepository;\n")
            .Write("tests/App.Tests/BlobRepository.Tests.cs", "namespace App.Tests;\n\npublic sealed partial class BlobRepositoryTests;\n")
            .Write("tests/App.Tests/BlobRepository.Lease.Tests.cs", "namespace App.Tests;\n\npublic sealed partial class BlobRepositoryTests;\n");

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("tests/App.Tests/BlobRepository.Tests.cs", "BlobRepository")]
    [InlineData("tests/App.Tests/BlobRepository.Lease.Tests.cs", "BlobRepositoryLeaseTests")]
    [InlineData("src/App/BlobRepository.Async.cs", "BlobRepositoryAsync")]
    public void A_test_or_aspect_file_named_for_another_type_is_a_breach(string file, string type)
    {
        using var tree = new RulesTree().Write(file, $"namespace App;\n\npublic sealed partial class {type};\n");

        Assert.Equal([("one-type-per-file", file)], tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/BlobRepository.Async.cs", "BlobRepository")]
    [InlineData("tests/App.Tests/BlobRepository.Lease.Tests.cs", "BlobRepositoryTests")]
    public void An_aspect_file_whose_type_is_not_partial_is_a_breach(string file, string type)
    {
        using var tree = new RulesTree().Write(file, $"namespace App;\n\npublic sealed class {type};\n");

        Assert.Equal([("one-type-per-file", file)], tree.Breaches());
    }

    [Theory]
    [InlineData("*.Spec.cs", "tests/App.Tests/Clock.Spec.cs")]
    [InlineData("*Spec.cs", "tests/App.Tests/ClockSpec.cs")]
    [InlineData("*Tests.cs", "tests/App.Tests/ClockTests.cs")]
    public void A_test_file_holds_its_subject_and_Tests_whatever_its_test_marker(string pattern, string file)
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "test-files", $"[\"{pattern}\"]")
            .Write(file, "namespace App.Tests;\n\npublic sealed class ClockTests;\n");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void The_test_file_names_come_from_the_placement_file()
    {
        using var tree = new RulesTree()
            .Set(PlacementFile, "test-files", "[\"*.Spec.cs\"]")
            .Write("tests/App.Tests/Clock.Spec.cs", "namespace App.Tests;\n\npublic sealed class ClockTests;\n")
            .Write("tests/App.Tests/Timer.Tests.cs", "namespace App.Tests;\n\npublic sealed class TimerTests;\n");

        Assert.Equal([("one-type-per-file", "tests/App.Tests/Timer.Tests.cs")], tree.Breaches());
    }

    [Fact]
    public void Program_cs_with_top_level_statements_is_not_a_breach()
    {
        using var tree = new RulesTree()
            .Write("src/App/Program.cs", """
                var app = WebApplication.Create(args);
                app.Run();

                public partial class Program;
                """);

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("src/App/AppHost.cs", "DistributedApplication.CreateBuilder(args).Build().Run();\n")]
    [InlineData("src/App/Program.cs", "WebApplication.Create(args).Run();\n\npublic sealed record Tick(DateTimeOffset At);\n")]
    public void Top_level_statements_outside_Program_cs_or_beside_another_type_are_a_breach(string file, string content)
    {
        using var tree = new RulesTree().Write(file, content);

        Assert.Equal([("one-type-per-file", file)], tree.Breaches());
    }
}
