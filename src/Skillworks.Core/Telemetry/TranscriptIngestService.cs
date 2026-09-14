using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.Telemetry;

public sealed class TranscriptIngestService(
    TranscriptIngestor ingestor,
    IngestState state,
    IOptions<TelemetryOptions> options,
    ILogger<TranscriptIngestService> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Hands startup back before any file is opened.
        await Task.Yield();

        var request = default(PassRequest);

        while (!stoppingToken.IsCancellationRequested)
        {
            await RunPassAsync(request, stoppingToken);

            try
            {
                request = await state.WaitForRequestAsync(options.Value.SweepInterval(), stoppingToken);
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    private async Task RunPassAsync(PassRequest request, CancellationToken stoppingToken)
    {
        state.PassStarted(request.Asked);

        var pass = new IngestPass(0, 0, request.Full);

        try
        {
            pass = await ingestor.RunAsync(request.Full, state.PassProgressed, stoppingToken);
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception failure)
        {
            // A pass that throws must not wedge the loop; the next request gets a fresh try.
            logger.LogError(failure, "Transcript ingest pass failed");
        }

        state.PassFinished(pass);
    }
}
