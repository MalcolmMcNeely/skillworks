using static Skillworks.Architecture.Tests.RulesTree;

namespace Skillworks.Architecture.Tests;

public sealed partial class ArchitectureCheckTests
{
    [Theory]
    [InlineData("var now = DateTime.Now;", "DateTime.Now")]
    [InlineData("var now = DateTime.UtcNow;", "DateTime.UtcNow")]
    [InlineData("var today = DateTime.Today;", "DateTime.Today")]
    [InlineData("var now = DateTimeOffset.Now;", "DateTimeOffset.Now")]
    [InlineData("var now = DateTimeOffset.UtcNow;", "DateTimeOffset.UtcNow")]
    [InlineData("var now = System.DateTimeOffset.UtcNow;", "DateTimeOffset.UtcNow")]
    [InlineData("var since = Stopwatch.StartNew();", "Stopwatch")]
    [InlineData("var since = new Stopwatch();", "Stopwatch")]
    [InlineData("Stopwatch since = null;", "Stopwatch")]
    [InlineData("var ticks = Environment.TickCount;", "Environment.TickCount")]
    [InlineData("var ticks = Environment.TickCount64;", "Environment.TickCount64")]
    [InlineData("Thread.Sleep(200);", "Thread.Sleep")]
    [InlineData("var waiting = Task.Delay(200);", "Task.Delay")]
    [InlineData("var timer = new Timer(_ => { });", "Timer")]
    [InlineData("var timer = new System.Threading.Timer(_ => { });", "Timer")]
    [InlineData("var beat = new PeriodicTimer(span);", "PeriodicTimer")]
    [InlineData("var spent = new CancellationTokenSource(span);", "CancellationTokenSource")]
    [InlineData("source.CancelAfter(span);", "CancelAfter")]
    [InlineData("client.Timeout = span;", "Timeout")]
    [InlineData("var client = new HttpClient { Timeout = span };", "Timeout")]
    [InlineData("var now = TimeProvider.System.GetUtcNow();", "TimeProvider.System")]
    [InlineData("TimeProvider clock = TimeProvider.System;", "TimeProvider.System")]
    [InlineData("return TimeProvider.System;", "TimeProvider.System")]
    public void A_reach_for_the_machine_clock_in_shipping_code_is_a_breach(string statement, string reach)
    {
        using var tree = Judging("app").Write("src/App/Clock.cs", Running("Clock", statement));

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("machine-clock", "src/App/Clock.cs"), (breach.Rule, breach.Path));
        Assert.Contains($"`{reach}`", breach.Message);
    }

    [Theory]
    [InlineData("var now = clock.GetUtcNow();")]
    [InlineData("var since = clock.GetTimestamp();")]
    [InlineData("var timer = clock.CreateTimer(callback, state, due, period);")]
    [InlineData("var spent = new CancellationTokenSource(span, clock);")]
    [InlineData("var beat = new PeriodicTimer(span, clock);")]
    [InlineData("var source = new CancellationTokenSource();")]
    [InlineData("var moment = DateTimeOffset.FromUnixTimeMilliseconds(value);")]
    [InlineData("var epoch = DateTimeOffset.UnixEpoch;")]
    [InlineData("var forever = Timeout.InfiniteTimeSpan;")]
    [InlineData("var seconds = options.TimeoutSeconds;")]
    public void A_wait_built_on_the_injected_clock_is_not_a_breach(string statement)
    {
        using var tree = Judging("app").Write("src/App/Clock.cs", Running("Clock", statement));

        Assert.Empty(tree.Breaches());
    }

    [Theory]
    [InlineData("services.TryAddSingleton(TimeProvider.System);")]
    [InlineData("services.AddSingleton<TimeProvider>(TimeProvider.System);")]
    public void Handing_the_real_clock_to_a_registration_is_not_a_breach(string statement)
    {
        using var tree = Judging("app").Write("src/App/Clock.cs", Running("Clock", statement));

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_reach_in_a_test_is_a_breach()
    {
        using var tree = Judging("app")
            .Write("tests/App.Tests/Clock.Tests.cs", Running("ClockTests", "Thread.Sleep(200);"));

        Assert.Equal([("machine-clock", "tests/App.Tests/Clock.Tests.cs")], tree.Breaches());
    }

    [Fact]
    public void A_reach_in_a_support_file_is_not_a_breach()
    {
        using var tree = Judging("app")
            .Support("Shared/Clock/TestTempo.cs", Running("TestTempo", "Thread.Sleep(200);"));

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_reach_written_inside_a_string_is_not_a_breach()
    {
        using var tree = Judging("app").Quoting("src/App/Sample.cs", "var now = DateTimeOffset.UtcNow;");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_file_named_for_a_reach_is_not_a_breach()
    {
        using var tree = Judging("app").Write("src/App/Stopwatch.cs");

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_context_the_rule_does_not_name_is_not_judged()
    {
        using var tree = new RulesTree()
            .Set(DeterminismFile, "contexts", "[check]")
            .Write("src/App/Clock.cs", Running("Clock", "Thread.Sleep(200);"))
            .Write("tools/Check/Clock.cs", Running("Clock", "Thread.Sleep(200);"));

        Assert.Equal([("machine-clock", "tools/Check/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_rule_that_names_no_context_judges_nothing()
    {
        using var tree = new RulesTree().Write("src/App/Clock.cs", Running("Clock", "Thread.Sleep(200);"));

        Assert.Empty(tree.Breaches());
    }

    [Fact]
    public void A_context_the_map_does_not_carry_is_a_breach()
    {
        using var tree = new RulesTree().Set(DeterminismFile, "contexts", "[app, ledger]");

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(("machine-clock", DeterminismFile), (breach.Rule, breach.Path));
        Assert.Contains("`ledger` names no context in `CONTEXT-MAP.md`", breach.Message);
    }

    [Fact]
    public void The_clock_comes_from_the_determinism_file()
    {
        using var tree = Judging("app")
            .Set(DeterminismFile, "clock", "Chronos")
            .Write("src/App/Clock.cs", Running("Clock", "var now = Chronos.System.GetUtcNow();"))
            .Write("src/App/Watch.cs", Running("Watch", "var now = TimeProvider.System.GetUtcNow();"));

        Assert.Equal([("machine-clock", "src/App/Clock.cs")], tree.Breaches());
    }

    [Fact]
    public void A_breach_names_the_reach_the_line_and_what_to_do()
    {
        using var tree = Judging("app").Write("src/App/Clock.cs", Running("Clock", "var now = DateTimeOffset.UtcNow;"));

        var breach = Assert.Single(tree.Check().Breaches);

        Assert.Equal(
            "machine-clock at src/App/Clock.cs: `DateTimeOffset.UtcNow` at line 5 reaches for the machine's clock. "
            + "Read now from the injected Clock: `clock.GetUtcNow()`.",
            breach.ToString());
    }

    [Fact]
    public void Each_reach_in_a_file_is_one_breach_that_names_every_line()
    {
        using var tree = Judging("app").Write("src/App/Clock.cs", """
            public sealed class Clock
            {
                public void Read()
                {
                    Thread.Sleep(200);
                    var now = DateTimeOffset.UtcNow;
                    var again = DateTimeOffset.UtcNow;
                }
            }
            """);

        var breaches = tree.Check().Breaches;

        Assert.Equal(
            [("machine-clock", "src/App/Clock.cs"), ("machine-clock", "src/App/Clock.cs")],
            breaches.Select(breach => (breach.Rule, breach.Path)));

        Assert.Contains("`Thread.Sleep` at line 5", breaches[0].Message);
        Assert.Contains("`DateTimeOffset.UtcNow` at lines 6, 7", breaches[1].Message);
    }

    [Fact]
    public void A_front_end_file_is_left_to_the_front_end_linter()
    {
        // The reach that breaches under any other extension, so the file is left alone for the
        // extension it carries and not for the words it happens to hold.
        using var tree = Judging("app").Write("web/src/clock.ts", Running("Clock", "var now = DateTimeOffset.UtcNow;"));

        Assert.Empty(tree.Breaches());
    }

    private static RulesTree Judging(string context) =>
        new RulesTree().Set(DeterminismFile, "contexts", $"[{context}]");

    private static string Running(string type, string statement) =>
        $"public sealed class {type}\n{{\n    public void Read()\n    {{\n        {statement}\n    }}\n}}\n";
}
