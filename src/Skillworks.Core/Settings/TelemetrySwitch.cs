using System.Text.Json.Nodes;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.Settings;

/// <summary>
/// The switch that makes Claude Code emit telemetry. It reports whether the variables Studio needs
/// are in place, and merges them into the developer's settings or takes them out again.
/// <para>
/// Two rules hold everywhere in here. It only ever touches <see cref="TelemetryVariables"/>, so
/// nothing else in the document can be lost. And it refuses to write a document it could not fully
/// parse, because a settings file it does not understand is one it would damage.
/// </para>
/// </summary>
public sealed class TelemetrySwitch(ClaudeSettingsFile file, IOptions<ClaudeSettingsOptions> options)
{
    /// <summary>
    /// Claude Code reads its settings once, at startup. Studio says so rather than leaving the
    /// developer to wonder why the events screen stays empty.
    /// </summary>
    public const string RestartNote =
        "A Claude Code session that is already running will not pick this up. Restart it.";

    public TelemetrySwitchState State()
    {
        var document = file.Read(options.Value.ResolvedPath());

        if (Unusable(document) is { } problem)
        {
            return Report(emitting: false, readable: false, [], problem);
        }

        var environment = document.Root!["env"] as JsonObject;

        var changes = Owned()
            .Where(variable => Held(environment, variable.Key) != variable.Value)
            .Select(variable => new TelemetryChange(variable.Key, Held(environment, variable.Key), variable.Value))
            .ToArray();

        return Report(emitting: changes.Length == 0, readable: true, changes, problem: null);
    }

    public TelemetrySwitchResult TurnOn()
    {
        var settingsPath = options.Value.ResolvedPath();
        var document = file.Read(settingsPath);

        if (Unusable(document) is { } problem)
        {
            return Refused(problem);
        }

        var root = document.Root!;
        var created = root["env"] is not JsonObject;
        var environment = created ? new JsonObject() : (JsonObject)root["env"]!;
        var previous = TelemetryStamp.Read(options.Value.ResolvedStampPath());
        var displaced = new Dictionary<string, string?>();

        foreach (var (name, value) in Owned())
        {
            var held = Held(environment, name);

            // A variable already at its target is either Studio's own value from last time or the
            // developer's own, and only the earlier stamp tells the two apart. Without one it is
            // theirs, and recording it as absent would delete it on the way back out.
            displaced[name] = held == value && previous.Displaced.TryGetValue(name, out var earlier)
                ? earlier
                : held;
            environment[name] = value;
        }

        if (created)
        {
            root["env"] = environment;
        }

        // The stamp goes down first, and deliberately. A crash between these two writes then leaves
        // a record of a write that never happened, which turning off ignores because the settings
        // never took Studio's values. The other order would lose the undo record instead.
        //
        // Studio owns the environment block from the moment it first created it, however many times
        // the switch is flipped afterwards.
        TelemetryStamp.Write(
            options.Value.ResolvedStampPath(),
            new TelemetryStamp(displaced, created || previous.CreatedEnvironment));

        file.Write(settingsPath, root);

        return new TelemetrySwitchResult(State(), null);
    }

    public TelemetrySwitchResult TurnOff()
    {
        var settingsPath = options.Value.ResolvedPath();
        var document = file.Read(settingsPath);

        if (Unusable(document) is { } problem)
        {
            return Refused(problem);
        }

        // No file means nothing was ever added, so there is nothing to take away and no reason to
        // create one.
        if (!document.Existed)
        {
            return new TelemetrySwitchResult(State(), null);
        }

        var root = document.Root!;
        var stampPath = options.Value.ResolvedStampPath();
        var stamp = TelemetryStamp.Read(stampPath);

        if (root["env"] is JsonObject environment)
        {
            foreach (var (name, value) in Owned())
            {
                // A value the developer has since changed by hand is not Studio's to take away.
                if (Held(environment, name) != value)
                {
                    continue;
                }

                if (stamp.Displaced.GetValueOrDefault(name) is { } original)
                {
                    environment[name] = original;
                }
                else
                {
                    environment.Remove(name);
                }
            }

            if (environment.Count == 0 && stamp.CreatedEnvironment)
            {
                root.Remove("env");
            }
        }

        file.Write(settingsPath, root);
        TelemetryStamp.Forget(stampPath);

        return new TelemetrySwitchResult(State(), null);
    }

    private IReadOnlyList<KeyValuePair<string, string>> Owned() =>
        TelemetryVariables.For(options.Value.CollectorEndpoint);

    /// <summary>
    /// Why the document cannot be merged into, or null when it can. An <c>env</c> that is not an
    /// object counts: overwriting it would throw away whatever the developer meant by it.
    /// </summary>
    private static string? Unusable(ClaudeSettingsDocument document) => document.Root switch
    {
        null => document.Problem ?? "it could not be parsed",
        var root when root["env"] is not null and not JsonObject => "its env is not an object",
        _ => null,
    };

    /// <summary>
    /// What a variable holds today. A settings file may spell a flag as a number, so the value is
    /// read as text rather than demanded as a string.
    /// </summary>
    private static string? Held(JsonObject? environment, string name) => environment?[name] switch
    {
        null => null,
        JsonValue value => value.ToString(),
        var node => node.ToJsonString(),
    };

    private TelemetrySwitchState Report(
        bool emitting,
        bool readable,
        IReadOnlyList<TelemetryChange> changes,
        string? problem) =>
        new(
            emitting,
            options.Value.ResolvedPath(),
            readable,
            options.Value.CollectorEndpoint,
            changes,
            RestartNote,
            problem);

    private TelemetrySwitchResult Refused(string problem) =>
        new(State(), $"Studio will not write {options.Value.ResolvedPath()}, because {problem}.");
}
