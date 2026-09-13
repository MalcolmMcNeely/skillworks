using Microsoft.EntityFrameworkCore;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Telemetry;

/// <summary>What one pass of the ingest got through.</summary>
/// <param name="TranscriptsRead">Files that had new content this pass, not files that exist.</param>
/// <param name="ActivationsAdded">Firings that were not already in the store.</param>
public readonly record struct IngestPass(int TranscriptsRead, int ActivationsAdded);

/// <summary>
/// Keeps the store level with the transcripts on disk. Point it at a folder and call it again
/// whenever; each pass reads only the bytes that arrived since the last one.
/// </summary>
public sealed class TranscriptIngestor(
    TranscriptLocator locator,
    RepositoryNames repositories,
    IDbContextFactory<TelemetryDbContext> contexts)
{
    public async Task<IngestPass> RunAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var cursors = await store.IngestedTranscripts.ToDictionaryAsync(t => t.Path, cancellationToken);
        var counted = await store.Activations.Select(a => a.ToolUseId).ToHashSetAsync(cancellationToken);

        var transcriptsRead = 0;
        var activationsAdded = 0;

        foreach (var path in locator.Transcripts())
        {
            cancellationToken.ThrowIfCancellationRequested();

            var cursor = cursors.GetValueOrDefault(path);
            var offset = cursor?.Offset ?? 0;
            var length = new FileInfo(path).Length;

            // Shorter than we left it means the file was replaced, not appended to. Start over.
            if (length < offset)
            {
                offset = 0;
            }

            if (length == offset)
            {
                continue;
            }

            transcriptsRead++;
            var readTo = offset;

            foreach (var line in TranscriptLines.From(path, offset))
            {
                cancellationToken.ThrowIfCancellationRequested();
                readTo = line.EndOffset;

                foreach (var activation in TranscriptParser.Activations(line.Text, repositories))
                {
                    if (counted.Add(activation.ToolUseId))
                    {
                        store.Activations.Add(activation);
                        activationsAdded++;
                    }
                }
            }

            if (cursor is null)
            {
                store.IngestedTranscripts.Add(new IngestedTranscript { Path = path, Offset = readTo });
            }
            else
            {
                cursor.Offset = readTo;
            }
        }

        await store.SaveChangesAsync(cancellationToken);

        return new IngestPass(transcriptsRead, activationsAdded);
    }
}
