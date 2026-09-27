using System.Text.RegularExpressions;

namespace Skillworks.Core.Shared.Stores;

public static class Refusal
{
    // A proxy in front of a store can answer with a whole page, and a Gap is read as one sentence.
    private const int LongestReason = 300;

    // The store's own words say why, where the status alone reads the same for every refusal.
    public static async Task<string> OfAsync(Uri address, HttpResponseMessage response, CancellationToken cancellationToken)
    {
        var said = await response.Content.ReadAsStringAsync(cancellationToken);
        var reason = Regex.Replace(said, @"\s+", " ").Trim().TrimEnd('.');

        if (reason.Length > LongestReason)
        {
            reason = $"{reason[..LongestReason]}…";
        }

        return reason.Length == 0
            ? $"{address} answered {(int)response.StatusCode}."
            : $"{address} answered {(int)response.StatusCode}: {reason}.";
    }
}
