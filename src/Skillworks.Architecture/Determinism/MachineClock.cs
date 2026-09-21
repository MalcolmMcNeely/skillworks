using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Skillworks.Architecture.Contexts;
using Skillworks.Architecture.Placement;
using Skillworks.Architecture.Placement.CSharp;

namespace Skillworks.Architecture.Determinism;

internal static class MachineClock
{
    public const string Rule = "machine-clock";

    private const string StopwatchName = "Stopwatch";
    private const string TimerName = "Timer";
    private const string PeriodicTimerName = "PeriodicTimer";
    private const string CancellationName = "CancellationTokenSource";
    private const string CancelAfterName = "CancelAfter";
    private const string ClientWaitName = "Timeout";

    private const string ReadNow = "Read now from the injected Clock: `clock.GetUtcNow()`.";

    private const string MeasureElapsed =
        "Measure elapsed time on the injected Clock: `clock.GetTimestamp()`, then `clock.GetElapsedTime(from)`.";

    private const string WaitOnAFact =
        "Wait on a fact. Where a delay is the fact, delay on the injected Clock: `clock.Delay(span)`.";

    private const string BuildOnTheClock = "Build the timer on the injected Clock: `clock.CreateTimer(...)`.";

    private const string CancelOnTheClock =
        "Give the cancellation the injected Clock: `new CancellationTokenSource(delay, clock)`.";

    private const string WaitAPatience =
        "Wait a Patience on the injected Clock, in the reader that waits. A client's own wait is measured on the " +
        "machine's clock whatever Clock is injected.";

    private static readonly Dictionary<string, string> StaticReaches = new(StringComparer.Ordinal)
    {
        ["DateTime.Now"] = ReadNow,
        ["DateTime.UtcNow"] = ReadNow,
        ["DateTime.Today"] = ReadNow,
        ["DateTimeOffset.Now"] = ReadNow,
        ["DateTimeOffset.UtcNow"] = ReadNow,
        ["Environment.TickCount"] = MeasureElapsed,
        ["Environment.TickCount64"] = MeasureElapsed,
        ["Thread.Sleep"] = WaitOnAFact,
        ["Task.Delay"] = WaitOnAFact,
    };

    public static IEnumerable<Breach> Check(
        string root,
        IReadOnlyList<string> sourceFiles,
        PlacementRules placement,
        ContextRules contexts,
        DeterminismRules determinism)
    {
        foreach (var breach in ContextsThatMatchNoContext(contexts, determinism))
            yield return breach;

        // Only C# is judged for time: finding a Reach needs a parser, and a text scan would report a name in a string.
        var judged = sourceFiles
            .Where(CSharpFile.IsCSharp)
            .Where(file => contexts.ClaimOf(file) is { } context && determinism.Judges(context.Name))
            .ToList();

        var projects = CSharpProject.AboveEach(root, judged.Select(SourceTree.FolderOf));

        foreach (var file in judged)
        {
            // A poll that waits for a container to be ready has to live somewhere, and a Support file is where.
            if (!placement.IsTestFile(Path.GetFileName(file)) && projects[SourceTree.FolderOf(file)] is { IsTests: true })
                continue;

            var tree = CSharpSyntaxTree.ParseText(File.ReadAllText(Path.Combine(root, file)));

            foreach (var (name, lines, fix) in ReachesIn(tree, determinism.Clock))
            {
                yield return new Breach(
                    Rule,
                    file,
                    $"`{name}` at {Breach.AtLines(lines)} reaches for the machine's clock. {fix}");
            }
        }
    }

    // A name no context carries judges nothing and would say nothing, so the list cannot go stale unnoticed.
    private static IEnumerable<Breach> ContextsThatMatchNoContext(ContextRules contexts, DeterminismRules determinism)
    {
        foreach (var name in determinism.Contexts
            .Where(name => contexts.Contexts.All(context => context.Name != name))
            .Order(StringComparer.Ordinal))
        {
            yield return new Breach(
                Rule,
                DeterminismRules.RelativePath,
                $"`{name}` names no context in `{ContextRules.RelativePath}`, so drop it or add the context.");
        }
    }

    private static IEnumerable<(string Name, IReadOnlyList<int> Lines, string Fix)> ReachesIn(SyntaxTree tree, string clock) =>
        Occurrences(tree.GetRoot(), clock)
            .Select(reach => (reach.Name, Line: tree.GetLineSpan(reach.Node.Span).StartLinePosition.Line + 1, reach.Fix))
            .OrderBy(reach => reach.Line)
            .GroupBy(reach => reach.Name, StringComparer.Ordinal)
            .OrderBy(reaches => reaches.First().Line)
            .Select(reaches => (
                reaches.Key,
                (IReadOnlyList<int>)[.. reaches.Select(reach => reach.Line).Distinct()],
                reaches.First().Fix));

    private static IEnumerable<(string Name, SyntaxNode Node, string Fix)> Occurrences(SyntaxNode root, string clock)
    {
        foreach (var node in root.DescendantNodes())
        {
            switch (node)
            {
                // Every use of the name is a reach, so `new Stopwatch()` needs no case of its own.
                case IdentifierNameSyntax { Identifier.Text: StopwatchName }:
                    yield return (StopwatchName, node, MeasureElapsed);
                    break;

                case MemberAccessExpressionSyntax access when Qualified(access) is { } name:
                    if (StaticReaches.TryGetValue(name, out var fix))
                        yield return (name, node, fix);
                    else if (name == $"{clock}.System" && !IsHandedOver(access))
                        yield return (name, node, HandOverInstead(name));

                    break;

                case ObjectCreationExpressionSyntax creation when TypeName(creation.Type) is { } built:
                    // The overloads that take the Clock are the longer ones, so the count of arguments says which was used.
                    var arguments = creation.ArgumentList?.Arguments.Count ?? 0;

                    if (built == TimerName)
                        yield return (TimerName, node, BuildOnTheClock);
                    else if (built == PeriodicTimerName && arguments < 2)
                        yield return (PeriodicTimerName, node, BuildOnTheClock);
                    else if (built == CancellationName && arguments == 1)
                        yield return (CancellationName, node, CancelOnTheClock);

                    break;

                case InvocationExpressionSyntax { Expression: MemberAccessExpressionSyntax { Name.Identifier.Text: CancelAfterName } }:
                    yield return (CancelAfterName, node, CancelOnTheClock);
                    break;

                case AssignmentExpressionSyntax assignment when SetsClientWait(assignment):
                    yield return (ClientWaitName, node, WaitAPatience);
                    break;
            }
        }
    }

    private static string HandOverInstead(string name) =>
        $"Hand `{name}` to a registration as the default, and read the Clock that was injected. Code that " +
        "names it anywhere else reads past the seam a test controls.";

    // Passing it to a registration is the whole of the permission: bound to a name, it is read and not handed over.
    private static bool IsHandedOver(MemberAccessExpressionSyntax access) => access.Parent is ArgumentSyntax;

    // An object initializer names the member alone, so the wait is set without a target to match on.
    private static bool SetsClientWait(AssignmentExpressionSyntax assignment) => assignment.Left switch
    {
        MemberAccessExpressionSyntax { Name.Identifier.Text: ClientWaitName } => true,
        IdentifierNameSyntax { Identifier.Text: ClientWaitName } => assignment.Parent is InitializerExpressionSyntax,
        _ => false,
    };

    private static string? Qualified(MemberAccessExpressionSyntax access) => access.Expression switch
    {
        IdentifierNameSyntax identifier => $"{identifier.Identifier.Text}.{access.Name.Identifier.Text}",
        MemberAccessExpressionSyntax inner => $"{inner.Name.Identifier.Text}.{access.Name.Identifier.Text}",
        _ => null,
    };

    private static string? TypeName(TypeSyntax type) => type switch
    {
        SimpleNameSyntax name => name.Identifier.Text,
        QualifiedNameSyntax qualified => qualified.Right.Identifier.Text,
        _ => null,
    };
}
