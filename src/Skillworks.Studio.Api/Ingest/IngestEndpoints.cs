using Skillworks.Core.Telemetry;

namespace Skillworks.Studio.Api.Ingest;

public static class IngestEndpoints
{
    public static IEndpointRouteBuilder MapIngestEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("ingest", (IngestReport report, CancellationToken cancellationToken) =>
            report.StatusAsync(cancellationToken));

        api.MapPost("ingest", async (IngestReport report, CancellationToken cancellationToken) =>
            Results.Accepted(value: await report.RequestPassAsync(full: false, cancellationToken)));

        // Its own route, not a query flag: a full re-ingest throws away everything read, so a typo must not reach it.
        api.MapPost("ingest/full", async (IngestReport report, CancellationToken cancellationToken) =>
            Results.Accepted(value: await report.RequestPassAsync(full: true, cancellationToken)));

        // No filter: a fault names a file rather than a skill, a repository or a moment a skill fired.
        api.MapGet("ingest/faults", (IngestReport report, CancellationToken cancellationToken) =>
            report.FaultsAsync(cancellationToken));

        return api;
    }
}
