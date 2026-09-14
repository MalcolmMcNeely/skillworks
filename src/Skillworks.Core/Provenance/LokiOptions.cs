namespace Skillworks.Core.Provenance;

public sealed class LokiOptions
{
    public const string SectionName = "Loki";

    // The AppHost pins this port, so the default needs no configuration.
    public string Address { get; set; } = Pinned;

    private const string Pinned = "http://localhost:3100";

    // Short on purpose: a Loki container that is down must cost the provenance, not the page.
    public int TimeoutSeconds { get; set; } = 5;

    // Loki refuses a range longer than 721 hours by default, so "everything" has to be a window.
    public int LookbackDays { get; set; } = 30;

    // Matches Loki's own ceiling on one answer.
    public int MaxEvents { get; set; } = 5000;

    // Ends in a slash, or a relative route resolved against it drops the last path segment.
    public Uri ResolvedAddress()
    {
        var address = string.IsNullOrWhiteSpace(Address) ? Pinned : Address.Trim();

        return new Uri(address.EndsWith('/') ? address : address + "/");
    }
}
