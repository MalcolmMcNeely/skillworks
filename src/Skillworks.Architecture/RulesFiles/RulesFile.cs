using System.Globalization;
using System.Text.RegularExpressions;
using YamlDotNet.Core;
using YamlDotNet.RepresentationModel;

namespace Skillworks.Architecture.RulesFiles;

internal sealed class RulesFile
{
    public const string Rule = "rules-file";

    private static readonly Regex YamlBlock = new(
        @"^```ya?ml[ \t]*\r?\n(.*?)^```",
        RegexOptions.Multiline | RegexOptions.Singleline);

    private readonly string _path;
    private readonly List<Breach> _breaches = [];
    private YamlMappingNode? _settings;

    private RulesFile(string path) => _path = path;

    public IReadOnlyList<Breach> Breaches => _breaches;

    public static RulesFile Load(string root, string path)
    {
        var file = new RulesFile(path);
        var full = Path.Combine(root, path);

        if (!File.Exists(full))
            file.Add("Create this file with a yaml block that holds the settings the check reads.");
        else
            file.Parse(File.ReadAllText(full));

        return file;
    }

    public int RequireWholeNumber(string key) =>
        Read<int?>(key, "a whole number above zero", node =>
            node is YamlScalarNode { Value: var text }
            && int.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out var number)
            && number > 0
                ? number
                : null)
        ?? 0;

    public IReadOnlyList<string> RequireList(string key) =>
        Read<IReadOnlyList<string>>(key, "a list, such as [a, b]", node =>
            node is YamlSequenceNode list && list.Children.All(IsText)
                ? [.. list.Children.Select(Text)]
                : null)
        ?? [];

    public IReadOnlyDictionary<string, string> RequireMap(string key, string shape, Func<string, bool> fitsKey) =>
        Read<IReadOnlyDictionary<string, string>>(key, shape, node =>
            node is YamlMappingNode map
            && map.Children.All(pair => IsText(pair.Key) && IsText(pair.Value) && fitsKey(Text(pair.Key)))
                ? map.Children.ToDictionary(pair => Text(pair.Key), pair => Text(pair.Value))
                : null)
        ?? new Dictionary<string, string>();

    public bool RequireTrueOrFalse(string key) =>
        Read<bool?>(key, "true or false", node =>
            node is YamlScalarNode { Value: var text } && bool.TryParse(text, out var value)
                ? value
                : null)
        ?? false;

    private void Parse(string text)
    {
        var blocks = YamlBlock.Matches(text);

        if (blocks.Count == 0)
        {
            Add("Add a ```yaml block that holds the settings the check reads.");
            return;
        }

        if (blocks.Count > 1)
        {
            Add("Merge the ```yaml blocks into one, so every setting is read from one place.");
            return;
        }

        var yaml = new YamlStream();
        try
        {
            yaml.Load(new StringReader(blocks[0].Groups[1].Value));
        }
        catch (YamlException exception)
        {
            Add($"Fix the yaml block: {exception.Message}");
            return;
        }

        switch (yaml.Documents)
        {
            case []:
                _settings = new YamlMappingNode();
                break;
            case [{ RootNode: YamlMappingNode settings }]:
                _settings = settings;
                break;
            default:
                Add("Write the yaml block as keys with values.");
                break;
        }
    }

    private T? Read<T>(string key, string shape, Func<YamlNode, T?> parse)
    {
        if (_settings is null)
            return default;

        if (!_settings.Children.TryGetValue(new YamlScalarNode(key), out var node))
        {
            Add($"Add `{key}` to the yaml block, set to {shape}.");
            return default;
        }

        var value = parse(node);
        if (value is null)
            Add($"Set `{key}` to {shape}.");

        return value;
    }

    private void Add(string message) => _breaches.Add(new Breach(Rule, _path, message));

    private static bool IsText(YamlNode node) => node is YamlScalarNode { Value.Length: > 0 };

    private static string Text(YamlNode node) => ((YamlScalarNode)node).Value!;
}
