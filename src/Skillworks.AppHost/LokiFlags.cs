namespace Skillworks.AppHost;

// The API tests start Loki with these too, so a passing test answers as fast, and within the same limits, as the app's Loki.
public static class LokiFlags
{
    // Cut by the hour, a month's read spends Studio's Patience joining parts; Grafana advises 6h-12h for one-process Loki.
    public static string[] Split =>
    [
        "-querier.split-queries-by-interval=12h",
        "-querier.split-instant-metric-queries-by-interval=12h",
    ];
}
