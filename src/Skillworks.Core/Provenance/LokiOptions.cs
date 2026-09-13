namespace Skillworks.Core.Provenance;

/// <summary>Where the events store is, and how far back it is worth asking it.</summary>
public sealed class LokiOptions
{
    public const string SectionName = "Loki";

    /// <summary>
    /// The store's own address. The AppHost pins the port, so the default is right on a machine
    /// that has never configured anything. Empty means the default too, because a variable set to
    /// nothing is a mistake rather than an address.
    /// </summary>
    public string Address { get; set; } = Pinned;

    private const string Pinned = "http://localhost:3100";

    /// <summary>
    /// Seconds to wait for an answer. Short on purpose: the transcript half of the screen is
    /// already in hand, and a container that is down must cost the provenance and not the page.
    /// </summary>
    public int TimeoutSeconds { get; set; } = 5;

    /// <summary>
    /// How far back a question with no start day reaches. Loki refuses a range longer than 721
    /// hours by default, so "everything" has to be a window, and every answer names the one it used.
    /// </summary>
    public int LookbackDays { get; set; } = 30;

    /// <summary>
    /// The most events one read takes, which is also Loki's own ceiling on one answer. A period
    /// with more than this keeps its newest and says that it did.
    /// </summary>
    public int MaxEvents { get; set; } = 5000;

    /// <summary>Trailing slash and all, because a relative request against it drops the last part.</summary>
    public Uri ResolvedAddress()
    {
        var address = string.IsNullOrWhiteSpace(Address) ? Pinned : Address.Trim();

        return new Uri(address.EndsWith('/') ? address : address + "/");
    }
}
