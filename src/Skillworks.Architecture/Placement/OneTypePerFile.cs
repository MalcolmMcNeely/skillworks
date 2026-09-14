using Skillworks.Architecture.Placement.CSharp;

namespace Skillworks.Architecture.Placement;

internal static class OneTypePerFile
{
    public const string Rule = "one-type-per-file";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules)
    {
        foreach (var file in sourceFiles.Where(CSharpFile.IsCSharp))
        {
            var csharp = CSharpFile.Read(root, file);
            var fileName = Path.GetFileName(file);
            var name = rules.NameOf(fileName);
            var expected = name.IsTest ? name.Subject + "Tests" : name.Subject;

            var types = csharp.TopLevelTypes
                .Where(type => !type.IsHidden)
                .DistinctBy(type => (type.Namespace, type.Name, type.Arity))
                .ToList();

            var own = types.FirstOrDefault(type => type.Name == expected);
            var others = types.Where(type => type != own).ToList();

            // Top-level statements make the Program type, so their file needs no type of its own.
            var needsOwnType = !csharp.HasTopLevelStatements;

            var fixes = new List<string>();

            if (csharp.HasTopLevelStatements && fileName != "Program.cs")
                fixes.Add("Move the top-level statements into `Program.cs`.");

            if (needsOwnType && own is null && others is [var only])
            {
                fixes.Add($"Rename `{only}` to `{expected}`, or rename the file for `{only}`.");
            }
            else
            {
                if (others is [var other])
                    fixes.Add($"Move `{other}` into a file of its own.");
                else if (others.Count > 1)
                    fixes.Add($"Move {string.Join(", ", others.Select(type => $"`{type}`"))} each into a file of its own.");

                if (needsOwnType && own is null)
                    fixes.Add($"Declare `{expected}` in this file, or delete the file.");
            }

            if (name.HasAspect && own is { IsPartial: false })
                fixes.Add($"Make `{own}` partial, or take the aspect out of the file name.");

            fixes.AddRange(csharp.NestedTypes
                .Where(type => !type.IsHidden)
                .Select(type => $"Make nested `{type}` private, or move it into a file of its own."));

            if (fixes.Count > 0)
                yield return new Breach(Rule, file, string.Join(' ', fixes));
        }
    }
}
