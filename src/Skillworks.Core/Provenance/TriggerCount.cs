namespace Skillworks.Core.Provenance;

// Trigger stays verbatim: putting it into words is the screen's job.
public sealed record TriggerCount(string? Trigger, int Activations)
{
    // A firing has one trigger however the skill was delivered, so the delivery groups fold into it.
    internal static IReadOnlyList<TriggerCount> Ordered(IEnumerable<(string? Trigger, decimal Activations)> counts) =>
    [
        .. counts
            .GroupBy(count => count.Trigger)
            .Select(same => new TriggerCount(same.Key, (int)same.Sum(count => count.Activations)))
            .OrderBy(count => count.Trigger, StringComparer.OrdinalIgnoreCase)
    ];
}
