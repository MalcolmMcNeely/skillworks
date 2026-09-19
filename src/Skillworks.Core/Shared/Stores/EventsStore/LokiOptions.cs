namespace Skillworks.Core.Shared.Stores.EventsStore;

public sealed class LokiOptions
{
    public const string SectionName = "Loki";

    // The AppHost pins this port, so the default needs no configuration.
    public string Address { get; set; } = Pinned;

    private const string Pinned = "http://localhost:3100";

    public string? Tenant { get; set; }

    // Short on purpose: a Loki container that is down must show as a Gap, not stall the page.
    public int PatienceSeconds { get; set; } = 5;

    public int LookbackDays { get; set; } = 7;

    // Loki refuses a range longer than 721 hours by default.
    public int MaxQueryDays { get; set; } = 30;

    // Ends in a slash, or a relative route resolved against it drops the last path segment.
    public Uri ResolvedAddress()
    {
        var address = string.IsNullOrWhiteSpace(Address) ? Pinned : Address.Trim();

        return new Uri(address.EndsWith('/') ? address : address + "/");
    }
}
