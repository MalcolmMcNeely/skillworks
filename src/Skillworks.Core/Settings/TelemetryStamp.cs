using System.Text.Json;

namespace Skillworks.Core.Settings;

// Kept with Studio's own data, not in the settings file, because that file belongs to the developer.
public sealed record TelemetryStamp(
    IReadOnlyDictionary<string, string?> Displaced,
    bool CreatedEnvironment)
{
    public static readonly TelemetryStamp Nothing = new(new Dictionary<string, string?>(), false);

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
