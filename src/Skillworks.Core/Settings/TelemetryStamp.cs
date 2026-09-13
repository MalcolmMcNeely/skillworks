using System.Text.Json;

namespace Skillworks.Core.Settings;

/// <summary>
/// What the switch displaced the last time it turned telemetry on: the value each variable held
/// before, and whether Studio created the environment block itself. It lives beside Studio's own
/// data rather than inside the settings file, because that file belongs to the developer.
/// </summary>
/// <param name="Displaced">A null value, or a missing key, means the variable was not there at all.</param>
public sealed record TelemetryStamp(
    IReadOnlyDictionary<string, string?> Displaced,
    bool CreatedEnvironment)
{
    public static readonly TelemetryStamp Nothing = new(new Dictionary<string, string?>(), false);

    /// <summary>A missing or unreadable stamp reads as nothing displaced, never as a failure.</summary>
    public static TelemetryStamp Read(string path)
    {
        try
        {
            return File.Exists(path)
                ? JsonSerializer.Deserialize<TelemetryStamp>(File.ReadAllText(path)) ?? Nothing
                : Nothing;
        }
        catch (Exception failure) when (failure is JsonException or IOException)
        {
            return Nothing;
        }
    }

    public static void Write(string path, TelemetryStamp stamp)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, JsonSerializer.Serialize(stamp));
    }

    public static void Forget(string path) => File.Delete(path);
}
