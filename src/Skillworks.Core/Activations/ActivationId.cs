using System.Globalization;
using Skillworks.Core.EventsStore;

namespace Skillworks.Core.Activations;

// Session and sequence name one firing; the moment lets opening it read seconds, not a week.
public sealed record ActivationId(string Session, string Sequence, DateTimeOffset At)
{
    private const char Separator = '_';

    // Wide, so an id's rounded millisecond never misses its event; session and sequence pick the firing.
    private static readonly TimeSpan Around = TimeSpan.FromSeconds(1);

    // Loki's nanosecond timestamps cannot hold a read around a moment outside these.
    private static readonly long Earliest = DateTimeOffset.UnixEpoch.AddDays(1).ToUnixTimeMilliseconds();

    private static readonly long Latest = new DateTimeOffset(2200, 1, 1, 0, 0, 0, TimeSpan.Zero).ToUnixTimeMilliseconds();

    internal DateTimeOffset ReadFrom => At - Around;

    internal DateTimeOffset ReadUntil => At + Around;

    internal static ActivationId Of(TelemetryEvent recorded) => new(
        recorded.Attribute(EventAttributes.Session) ?? "",
        recorded.Attribute(EventAttributes.Sequence) ?? "",
        recorded.At);

    // The session takes what is left, as it is the one part that might hold the separator.
    internal static ActivationId? Parse(string id)
    {
        var parts = id.Split(Separator);

        if (parts.Length < 3 ||
            !long.TryParse(parts[^1], NumberStyles.None, CultureInfo.InvariantCulture, out var milliseconds) ||
            milliseconds < Earliest ||
            milliseconds > Latest)
        {
            return null;
        }

        return new ActivationId(
            string.Join(Separator, parts[..^2]),
            parts[^2],
            DateTimeOffset.FromUnixTimeMilliseconds(milliseconds));
    }

    public override string ToString() =>
        string.Join(Separator, Session, Sequence, At.ToUnixTimeMilliseconds().ToString(CultureInfo.InvariantCulture));
}
