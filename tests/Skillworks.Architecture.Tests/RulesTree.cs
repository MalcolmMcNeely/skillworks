namespace Skillworks.Architecture.Tests;

public sealed class RulesTree : IDisposable
{
    public const string PlacementFile = ".claude/rules/file-placement.md";
    public const string CommentsFile = ".claude/rules/comments.md";
    public const string WordsFile = ".claude/rules/words.md";
    public const string ContextMapFile = "CONTEXT-MAP.md";

    private readonly DirectoryInfo _root = Directory.CreateTempSubdirectory("skillworks-architecture");

    private readonly List<string> _projects = [];

    private readonly Dictionary<string, (string Glossary, IReadOnlyList<string> Code)> _contexts = new()
    {
        ["app"] = ("CONTEXT.md", ["src", "tests", "web"]),
        ["check"] = ("tools/Check/CONTEXT.md", ["tools/Check"]),
    };

    private readonly Dictionary<string, Dictionary<string, string>> _settings = new()
    {
        [PlacementFile] = new()
        {
            ["slices"] = "[Watch, Sessions]",
            ["concerns"] = "[api, components, lib, routes]",
            ["max-types-per-folder"] = "10",
            ["source-files"] = "[.cs, .ts, .tsx]",
            ["test-files"] = "[\"*.Tests.cs\", \"*.test.ts\", \"*.test.tsx\"]",
            ["skip-folders"] = "[Migrations, bin, obj, node_modules]",
            ["banned-folder-names"] = "[utils, helpers, common, misc]",
            ["name-map"] = "{\"*Queries\": Queries}",
        },
        [CommentsFile] = new()
        {
            ["doc-comments"] = "false",
        },
        [WordsFile] = new()
        {
            ["banned-words"] = "{app: [Widget, \"Gadget box\"], check: []}",
            ["skip-folders"] = "[sketches]",
        },
    };

    public RulesTree()
    {
        foreach (var file in _settings.Keys)
            WriteRules(file);

        foreach (var context in _contexts.Values)
            Write(context.Glossary, "# Glossary\n\nThe words this context settled on.\n");

        WriteContextMap();
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

    public RulesTree SetContext(string name, string glossary, params string[] code)
    {
        _contexts[name] = (glossary, code);
        return WriteContextMap();
    }

    public RulesTree RemoveContext(string name)
    {
        _contexts.Remove(name);
        return WriteContextMap();
    }

    // A project turns on the namespace rule, so a file beneath one is written with the namespace its folder asks for.
    public RulesTree Project(string folder)
    {
        _projects.Add(folder);
        return Write($"{folder}/{Path.GetFileName(folder)}.csproj", "<Project Sdk=\"Microsoft.NET.Sdk\" />\n");
    }

    public RulesTree FrontEnd(string folder) => Write($"{folder}/package.json", "{}\n");

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

    public CheckResult Check(params string[] alsoRun) => ArchitectureCheck.Run(_root.FullName, alsoRun);

    public IEnumerable<(string Rule, string Path)> Breaches(params string[] alsoRun) =>
        Check(alsoRun).Breaches.Select(breach => (breach.Rule, breach.Path));

    public void Dispose() => _root.Delete(recursive: true);

    // A C# file with no content breaks the one-type rule, which would crowd the breaches of every other rule.
    private string TypeNamedFor(string path)
    {
        var fileName = Path.GetFileName(path);
        if (!fileName.EndsWith(".cs", StringComparison.Ordinal))
            return "";

        var subject = fileName.Split('.')[0];
        var name = fileName.EndsWith(".Tests.cs", StringComparison.Ordinal) ? $"{subject}Tests" : subject;

        return $"{NamespaceOf(path)}public sealed partial class {name};\n";
    }

    private string NamespaceOf(string path)
    {
        var folder = path.LastIndexOf('/') is var slash and >= 0 ? path[..slash] : "";

        var project = _projects
            .Where(candidate => folder == candidate || folder.StartsWith($"{candidate}/", StringComparison.Ordinal))
            .MaxBy(candidate => candidate.Length);

        if (project is null)
            return "";

        var beneath = folder[project.Length..].Trim('/').Replace('/', '.');
        var root = Path.GetFileName(project);

        return $"namespace {(beneath.Length == 0 ? root : $"{root}.{beneath}")};\n\n";
    }

    private RulesTree WriteRules(string file)
    {
        var settings = string.Join('\n', _settings[file].Select(setting => $"{setting.Key}: {setting.Value}"));
        return Write(file, $"# Rules\n\nThe text for Claude.\n\n```yaml\n{settings}\n```\n");
    }

    private RulesTree WriteContextMap()
    {
        var contexts = _contexts.Select(context => string.Join(
            '\n',
            [
                $"  {context.Key}:",
                $"    glossary: {context.Value.Glossary}",
                "    code:",
                .. context.Value.Code.Select(path => $"      - {path}"),
            ]));

        return Write(
            ContextMapFile,
            $"# Context Map\n\nThe text for Claude.\n\n```yaml\ncontexts:\n{string.Join('\n', contexts)}\n```\n");
    }
}
