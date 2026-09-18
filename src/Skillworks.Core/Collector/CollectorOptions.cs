namespace Skillworks.Core.Collector;

public sealed class CollectorOptions
{
    public const string SectionName = "Collector";

    // The AppHost pins this port, so the default needs no configuration.
    public string Address { get; set; } = Pinned;

    private const string Pinned = "http://localhost:4318";

    // Short on purpose: a Collector that is down must light its own Lamp, not hold the panel up.
    public int TimeoutSeconds { get; set; } = 5;

    // Every reader settles a blank the same way, or the knock and the settings fall back to different addresses.
    public string ResolvedEndpoint() => string.IsNullOrWhiteSpace(Address) ? Pinned : Address.Trim();

    // Ends in a slash, or a relative route resolved against it drops the last path segment.
    public Uri ResolvedAddress()
    {
        var endpoint = ResolvedEndpoint();

        return new Uri(endpoint.EndsWith('/') ? endpoint : endpoint + "/");
    }
}
