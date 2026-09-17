namespace Skillworks.Core.Sessions.Context;

// No event carries the size of a context window, so a model id with no marker leaves the limit unknown, never guessed.
public static class ContextLimit
{
    private const string MillionMarker = "[1m]";

    private const long Million = 1_000_000;

    public static long? Of(string? model) =>
        model?.Contains(MillionMarker, StringComparison.OrdinalIgnoreCase) == true ? Million : null;

    // A model id that states no window contradicts none that does, so a Subagent on a smaller model costs no limit.
    public static long? Stated(IEnumerable<string?> models) => models.Select(Of).Max();
}
