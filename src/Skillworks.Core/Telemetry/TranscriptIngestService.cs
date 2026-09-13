using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Skillworks.Core.Telemetry;

/// <summary>
/// Runs the ingest in the background: one pass at startup, then one for every request that arrives.
/// Studio serves pages while 678 MB is still being read.
/// </summary>
public sealed class TranscriptIngestService(
    TranscriptIngestor ingestor,
    IngestState state,
    ILogger<TranscriptIngestService> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Hands startup back before any file is opened.
        await Task.Yield();

        while (!stoppingToken.IsCancellationRequested)
        {
            await RunPassAsync(stoppingToken);

            try
            {
                await state.WaitForRequestAsync(stoppingToken);
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    private async Task RunPassAsync(CancellationToken stoppingToken)
    {
        state.PassStarted();

        var pass = default(IngestPass);

        try
        {
            pass = await ingestor.RunAsync(stoppingToken);
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
