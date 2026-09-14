namespace Skillworks.Core.Telemetry;

internal readonly record struct LineReading(
    IReadOnlyList<Activation> Activations,
    Turn? Turn,
    string? Problem);
