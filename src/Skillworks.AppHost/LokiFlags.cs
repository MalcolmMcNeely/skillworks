namespace Skillworks.AppHost;

// The API tests start Loki with these too, so a passing test answers as fast, and within the same limits, as the app's Loki.
public static class LokiFlags
{
    public static string[] All =>
    [
        // Cut by the hour, a month's read spends Studio's Patience joining parts; Grafana advises 6h-12h for one-process Loki.
        "-querier.split-queries-by-interval=12h",
        "-querier.split-instant-metric-queries-by-interval=12h",
        // One Sessions list load queues about 150 parts, and at Loki's default of four they wait past a read's Patience.
        "-querier.max-concurrent=16",
        // Loki's embedded cache holds these, so a reload reuses the parts it already worked out.
        "-querier.cache-results=true",
        "-querier.cache-instant-metric-results=true",
        "-querier.instant-metric-query-split-align=true",
        // A test reads events it pushed minutes before, so the newest answers must never come from the cache.
        "-frontend.max-cache-freshness=10m",
    ];
}
