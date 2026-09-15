namespace Skillworks.Architecture.Tests;

public sealed class RulesTree : IDisposable
{
    public const string PlacementFile = ".claude/rules/file-placement.md";
    public const string CommentsFile = ".claude/rules/comments.md";

    private readonly DirectoryInfo _root = Directory.CreateTempSubdirectory("skillworks-architecture");

    private readonly Dictionary<string, Dictionary<string, string>> _settings = new()
    {
        [PlacementFile] = new()
        {
            ["max-types-per-folder"] = "10",
            ["source-files"] = "[.cs, .ts, .tsx]",
            ["test-files"] = "[\"*.Tests.cs\", \"*.test.ts\", \"*.test.tsx\"]",
            ["skip-folders"] = "[Migrations, bin, obj, node_modules]",
            ["banned-folder-names"] = "[utils, helpers, common, shared, misc]",
            ["name-map"] = "{\"*Queries\": Queries}",
        },
        [CommentsFile] = new()
        {
            ["doc-comments"] = "false",
        },
    };

    public RulesTree()
    {
        foreach (var file in _settings.Keys)
            WriteRules(file);
    }

    public RulesTree Set(string file, string key, string value)
    {
        _settings[file][key] = value;
        return WriteRules(file);
    }

    public RulesTree Remove(string file, string key)
    {
        _settings[file].Remove(key);
        return WriteRules(file);
    }

    public RulesTree Write(string path, string? content = null)
    {
        var full = Path.Combine(_root.FullName, path);
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllText(full, content ?? TypeNamedFor(path));
        return this;
    }

    public RulesTree Delete(string path)
    {
        File.Delete(Path.Combine(_root.FullName, path));
        return this;
    }

    public CheckResult Check() => ArchitectureCheck.Run(_root.FullName);

    public IEnumerable<(string Rule, string Path)> Breaches() =>
        Check().Breaches.Select(breach => (breach.Rule, breach.Path));

    public void Dispose() => _root.Delete(recursive: true);

    // A C# file with no content breaks the one-type rule, which would crowd the breaches of every other rule.
    private static string TypeNamedFor(string path)
    {
        var fileName = Path.GetFileName(path);
        if (!fileName.EndsWith(".cs", StringComparison.Ordinal))
            return "";

        var subject = fileName.Split('.')[0];
        return fileName.EndsWith(".Tests.cs", StringComparison.Ordinal)
            ? $"public sealed partial class {subject}Tests;\n"
            : $"public sealed partial class {subject};\n";
    }

    private RulesTree WriteRules(string file)
    {
        var settings = string.Join('\n', _settings[file].Select(setting => $"{setting.Key}: {setting.Value}"));
        return Write(file, $"# Rules\n\nThe text for Claude.\n\n```yaml\n{settings}\n```\n");
    }
}
