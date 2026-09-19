using System.Text.Json.Nodes;
using Microsoft.Extensions.Options;
using Skillworks.Core.Shared.Stores.Collector;

namespace Skillworks.Core.Shared.Telemetry;

// The address it writes is the one Health knocks on, so a Lamp can never pass a door nothing is sent to.
public sealed class TelemetrySwitch(
    ClaudeSettingsFile file,
    IOptions<ClaudeSettingsOptions> options,
    IOptions<CollectorOptions> collector)
{
    public const string RestartNote =
        "A Claude Code session that is already running will not pick this up. Restart it.";

    public const string TurnOnNote = "Turn telemetry on with the Telemetry switch. " + RestartNote;

    public TelemetrySwitchState State()
    {
        var document = file.Read(options.Value.ResolvedPath());

        if (Unusable(document) is { } problem)
        {
            return Report(emitting: false, readable: false, problem);
        }

        var environment = Environment(document);

        // All of them or none: a machine holding some of them records a Session nobody can read in full.
        var emitting = Owned().All(variable => Held(environment, variable.Key) == variable.Value);

        return Report(emitting, readable: true, problem: null);
    }

    public bool? TracesOn() => On(TelemetryVariables.Traces);

    public bool? WordsOn() => On(TelemetryVariables.Words);

    // A guess of off would send a developer to write a file Studio has refused.
    private bool? On(IReadOnlyList<KeyValuePair<string, string>> group)
    {
        var document = file.Read(options.Value.ResolvedPath());

        return Unusable(document) is null
            ? group.All(variable => Held(Environment(document), variable.Key) == variable.Value)
            : null;
    }

    // Asked only once Unusable has passed, which is what says the document has a root at all.
    private static JsonObject? Environment(ClaudeSettingsDocument document) => document.Root!["env"] as JsonObject;

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
        var stampPath = options.Value.ResolvedStampPath();
        var previous = TelemetryStamp.Read(stampPath);
        var displaced = new Dictionary<string, string?>();

        foreach (var (name, value) in Owned())
        {
            var held = Held(environment, name);

            // Without an earlier stamp the value is the developer's, and recording it absent would delete it on turning off.
            displaced[name] = held == value && previous.Displaced.TryGetValue(name, out var earlier)
                ? earlier
                : held;
            environment[name] = value;
        }

        if (created)
        {
            root["env"] = environment;
        }

        // Stamp first, or a crash between the writes loses the undo; an env block Studio once created stays Studio's.
        TelemetryStamp.Write(stampPath, new TelemetryStamp(displaced, created || previous.CreatedEnvironment));

        if (file.Write(settingsPath, root) is { } failure)
        {
            // A refused write displaced nothing, and a stamp saying otherwise would delete the developer's own env block.
            TelemetryStamp.Write(stampPath, previous);

            return Unwritten(failure);
        }

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

        // No file means nothing was ever added, so there is nothing to take away and no reason to create one.
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

        if (file.Write(settingsPath, root) is { } failure)
        {
            return Unwritten(failure);
        }

        TelemetryStamp.Forget(stampPath);

        return new TelemetrySwitchResult(State(), null);
    }

    private IReadOnlyList<KeyValuePair<string, string>> Owned() =>
        TelemetryVariables.For(collector.Value.ResolvedEndpoint());

    // A non-object env counts: overwriting it would discard whatever the developer meant by it.
    private static string? Unusable(ClaudeSettingsDocument document) => document.Root switch
    {
        null => document.Problem ?? "it could not be parsed",
        var root when root["env"] is not null and not JsonObject => "its env is not an object",
        _ => null,
    };

    // A settings file may spell a flag as a number, so any JSON value is read as its text.
    private static string? Held(JsonObject? environment, string name) => environment?[name] switch
    {
        null => null,
        JsonValue value => value.ToString(),
        var node => node.ToJsonString(),
    };

    private TelemetrySwitchState Report(bool emitting, bool readable, string? problem) =>
        new(
            emitting,
            options.Value.ResolvedPath(),
            readable,
            collector.Value.ResolvedEndpoint(),
            RestartNote,
            problem,
            TeamSettings.For(file, collector.Value.ResolvedEndpoint()));

    private TelemetrySwitchResult Refused(string problem) =>
        new(State(), $"Studio will not write {options.Value.ResolvedPath()}, because {problem}.");

    private TelemetrySwitchResult Unwritten(string failure) =>
        new(State(), $"Studio could not write {options.Value.ResolvedPath()}, so nothing was changed: {failure}");
}
