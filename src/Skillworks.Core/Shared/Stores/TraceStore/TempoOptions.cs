namespace Skillworks.Core.Shared.Stores.TraceStore;

public sealed class TempoOptions
{
    public const string SectionName = "Tempo";

    // The AppHost pins this port, so the default needs no configuration.
    public string Address { get; set; } = Pinned;

    private const string Pinned = "http://localhost:3200";

    public string? Tenant { get; set; }

    // Short on purpose: a Tempo container that is down must show as a Gap, not stall the page.
    public int RequestPatienceSeconds { get; set; } = 5;

    // One session's read is hundreds of requests.
    public int SessionPatienceSeconds { get; set; } = 30;

    // The store refuses a search longer than a week by default.
    public int MaxSearchDays { get; set; } = 7;

    // A long interactive Session is a few hundred traces, and the store's own default of 20 would cut it short.
    public int MostTraces { get; set; } = 1000;

    // Well past a busy week, so a read that fills this up is one the reader has to be told about.
    public int MostSessions { get; set; } = 1000;

    // Ends in a slash, or a relative route resolved against it drops the last path segment.
    public Uri ResolvedAddress()
    {
        var address = string.IsNullOrWhiteSpace(Address) ? Pinned : Address.Trim();

        return new Uri(address.EndsWith('/') ? address : address + "/");
    }
}
