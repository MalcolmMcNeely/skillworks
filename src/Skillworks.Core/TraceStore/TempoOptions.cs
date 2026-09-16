namespace Skillworks.Core.TraceStore;

public sealed class TempoOptions
{
    public const string SectionName = "Tempo";

    // The AppHost pins this port, so the default needs no configuration.
    public string Address { get; set; } = Pinned;

    private const string Pinned = "http://localhost:3200";

    public string? Tenant { get; set; }

    // Short on purpose: a Tempo container that is down must show as a Gap, not stall the page.
    public int TimeoutSeconds { get; set; } = 5;

    // Ends in a slash, or a relative route resolved against it drops the last path segment.
    public Uri ResolvedAddress()
    {
        var address = string.IsNullOrWhiteSpace(Address) ? Pinned : Address.Trim();

        return new Uri(address.EndsWith('/') ? address : address + "/");
    }
}
