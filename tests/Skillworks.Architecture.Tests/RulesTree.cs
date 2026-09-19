namespace Skillworks.Architecture.Tests;

public sealed class RulesTree : IDisposable
{
    public const string PlacementFile = ".claude/rules/file-placement.md";
    public const string CommentsFile = ".claude/rules/comments.md";
    public const string WordsFile = ".claude/rules/words.md";
    public const string ContextMapFile = "CONTEXT-MAP.md";

    private readonly DirectoryInfo _root = Directory.CreateTempSubdirectory("skillworks-architecture");

    private readonly List<string> _projects = [];

    private readonly Dictionary<string, Claim> _contexts = new()
    {
        ["app"] = new("CONTEXT.md", Slices: true, ["src", "tests", "web"]),
        ["check"] = new("tools/Check/CONTEXT.md", Slices: false, ["tools/Check"]),
    };

    // Every folder in Shared names a glossary word, so the default settles the words the trees are written with.
    private readonly Dictionary<string, IReadOnlyList<string>> _headwords = new()
    {
        ["app"] = ["Alarm", "Catalogue", "Clock", "Health", "Host", "Snooze", "Timer", "Wire"],
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

        foreach (var context in _contexts.Keys)
            WriteGlossary(context);

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

    public RulesTree SetContext(string name, string glossary, bool slices, params string[] code)
    {
        _contexts[name] = new Claim(glossary, slices, code);
        return WriteContextMap();
    }

    public RulesTree Slices(string name, bool declared)
    {
        _contexts[name] = _contexts[name] with { Slices = declared };
        return WriteContextMap();
    }

    public RulesTree Glossary(string context, params string[] headwords)
    {
        _headwords[context] = headwords;
        return WriteGlossary(context);
    }

    public RulesTree RemoveContext(string name)
    {
        _contexts.Remove(name);
        return WriteContextMap();
    }

    // A project turns on the namespace rule, so a file beneath one is written with the namespace its folder asks for.
    public RulesTree Project(string folder, params string[] usings)
    {
        _projects.Add(folder);

        var items = string.Join('\n', usings.Select(name => $"    <Using Include=\"{name}\" />"));

        return Write(
            $"{folder}/{Path.GetFileName(folder)}.csproj",
            usings.Length == 0
                ? "<Project Sdk=\"Microsoft.NET.Sdk\" />\n"
                : $"<Project Sdk=\"Microsoft.NET.Sdk\">\n  <ItemGroup>\n{items}\n  </ItemGroup>\n</Project>\n");
    }

    public RulesTree FrontEnd(string folder) => Write($"{folder}/package.json", "{}\n");

    public RulesTree Write(string path, string? content = null)
    {
        var full = Path.Combine(_root.FullName, path);
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        File.WriteAllText(full, content ?? TypeNamedFor(path));
        return this;
    }

    public RulesTree Reads(string path, params string[] namespaces)
    {
        var usings = string.Concat(namespaces.Select(name => $"using {name};\n"));
        return Write(path, $"{usings}\n{TypeNamedFor(path)}");
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

    private RulesTree WriteGlossary(string context)
    {
        var headwords = _headwords.TryGetValue(context, out var chosen) ? chosen : [];
        var entries = headwords.Select(headword => $"**{headword}**:\nWhat this context means by it.\n");

        return Write(
            _contexts[context].Glossary,
            $"# Glossary\n\nThe words this context settled on.\n\n{string.Join('\n', entries)}");
    }

    private RulesTree WriteContextMap()
    {
        var contexts = _contexts.Select(context => string.Join(
            '\n',
            [
                $"  {context.Key}:",
                $"    glossary: {context.Value.Glossary}",
                $"    slices: {(context.Value.Slices ? "true" : "false")}",
                "    code:",
                .. context.Value.Code.Select(path => $"      - {path}"),
            ]));

        return Write(
            ContextMapFile,
            $"# Context Map\n\nThe text for Claude.\n\n```yaml\ncontexts:\n{string.Join('\n', contexts)}\n```\n");
    }

    private sealed record Claim(string Glossary, bool Slices, IReadOnlyList<string> Code);
}
