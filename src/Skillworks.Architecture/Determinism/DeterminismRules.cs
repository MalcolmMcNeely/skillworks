using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Determinism;

internal sealed record DeterminismRules(string Clock, IReadOnlyList<string> Contexts)
{
    public const string RelativePath = ".claude/rules/determinism.md";

    public static DeterminismRules Read(RulesFile file) =>
        new(
            file.RequireText("clock", "the name of the type Studio asks what the time is"),
            file.RequireList("contexts"));

    public bool Judges(string contextName) => Contexts.Contains(contextName, StringComparer.Ordinal);
}
