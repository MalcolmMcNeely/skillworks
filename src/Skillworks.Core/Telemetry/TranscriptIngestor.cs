using Microsoft.EntityFrameworkCore;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Telemetry;

/// <summary>What one pass of the ingest got through.</summary>
/// <param name="TranscriptsRead">Files that had new content this pass, not files that exist.</param>
/// <param name="ActivationsAdded">Firings that were not already in the store.</param>
/// <param name="Full">The pass threw away what was already read and read it all again.</param>
public readonly record struct IngestPass(int TranscriptsRead, int ActivationsAdded, bool Full);

/// <summary>How far a pass in flight has got, so an empty screen can say which it is.</summary>
public readonly record struct IngestProgress(int TranscriptsSeen, int TranscriptsTotal);

/// <summary>
/// Keeps the store level with the transcripts on disk. Point it at a folder and call it again
/// whenever; each pass reads only the bytes that arrived since the last one.
/// </summary>
public sealed class TranscriptIngestor(
    TranscriptLocator locator,
    RepositoryNames repositories,
    IDbContextFactory<TelemetryDbContext> contexts,
    TimeProvider clock)
{
    /// <summary>What one transcript gave the pass it was read in.</summary>
    private readonly record struct TranscriptRead(bool HadNewContent, int ActivationsAdded);

    /// <summary>What the pass already knows when it reaches a file, carried from file to file.</summary>
    /// <param name="Cursors">How far each file was read last time, updated as the pass goes.</param>
    /// <param name="Counted">Tool use ids already in the store, so a re-read cannot double count.</param>
    /// <param name="Unreadable">Files carrying a standing fault, so it can be cleared when one opens.</param>
    private sealed record Known(
        Dictionary<string, IngestedTranscript> Cursors,
        HashSet<string> Counted,
        HashSet<string> Unreadable);

    /// <param name="full">True forgets everything already read and reads it all again.</param>
    /// <param name="progress">Called once per transcript, so a caller can show how far it has got.</param>
    public async Task<IngestPass> RunAsync(
        bool full,
        Action<IngestProgress> progress,
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        if (full)
        {
            await store.Activations.ExecuteDeleteAsync(cancellationToken);
            await store.IngestedTranscripts.ExecuteDeleteAsync(cancellationToken);
            await store.TranscriptFaults.ExecuteDeleteAsync(cancellationToken);
        }

        var known = new Known(
            await store.IngestedTranscripts.ToDictionaryAsync(t => t.Path, cancellationToken),
            await store.Activations.Select(a => a.ToolUseId).ToHashSetAsync(cancellationToken),
            await store.TranscriptFaults
                .Where(f => f.Line == TranscriptFault.WholeFile)
                .Select(f => f.Path)
                .ToHashSetAsync(cancellationToken));

        var transcripts = locator.Transcripts();
        progress(new IngestProgress(0, transcripts.Count));

        var transcriptsRead = 0;
        var activationsAdded = 0;
        var seen = 0;

        foreach (var path in transcripts)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var read = await ReadAsync(store, known, path, cancellationToken);

            transcriptsRead += read.HadNewContent ? 1 : 0;
            activationsAdded += read.ActivationsAdded;

            progress(new IngestProgress(++seen, transcripts.Count));
        }

        return new IngestPass(transcriptsRead, activationsAdded, full);
    }

    private async Task<TranscriptRead> ReadAsync(
        TelemetryDbContext store,
        Known known,
        string path,
        CancellationToken cancellationToken)
    {
        var file = new FileInfo(path);

        // The listing was taken a moment ago, so a session deleted since then is ordinary.
        if (!file.Exists)
        {
            return default;
        }

        var cursor = known.Cursors.GetValueOrDefault(path);
        var offset = cursor?.Offset ?? 0;
        var lines = cursor?.Lines ?? 0;

        // Shorter than we left it means the file was replaced, not appended to. Start over.
        var restarted = file.Length < offset;

        if (restarted)
        {
            offset = 0;
            lines = 0;
        }

        if (file.Length == offset)
        {
            return default;
        }

        var fresh = new List<Activation>();
        var faults = new List<TranscriptFault>();
        var firstSeenHere = new HashSet<string>();
        var readTo = offset;

        try
        {
            foreach (var line in TranscriptLines.From(path, offset))
            {
                cancellationToken.ThrowIfCancellationRequested();
                readTo = line.EndOffset;
                lines++;

                var reading = TranscriptParser.Read(line.Text, repositories);

                if (reading.Problem is { } problem)
                {
                    faults.Add(Fault(path, lines, problem));
                    continue;
                }

                foreach (var activation in reading.Activations)
                {
                    if (!known.Counted.Contains(activation.ToolUseId) &&
                        firstSeenHere.Add(activation.ToolUseId))
                    {
                        fresh.Add(activation);
                    }
                }
            }
        }
        catch (Exception failure) when (failure is not OperationCanceledException)
        {
            // Nothing was written and the cursor has not moved, so the file is left exactly as it
            // was. One transcript that will not open must not cost the other 1,470.
            await RefuseAsync(store, known, Fault(path, TranscriptFault.WholeFile, failure.Message), cancellationToken);

            return default;
        }

        var opened = known.Unreadable.Remove(path);

        if (restarted)
        {
            // Every line is about to be read again, so the faults from the old contents would
            // collide with the ones this pass is finding.
            await store.TranscriptFaults.Where(f => f.Path == path).ExecuteDeleteAsync(cancellationToken);
        }
        else if (opened)
        {
            // Only the standing "would not open" goes. Lines this file lost earlier were never
            // re-read, so dropping them here would quietly undercount them for good.
            await store.TranscriptFaults
                .Where(f => f.Path == path && f.Line == TranscriptFault.WholeFile)
                .ExecuteDeleteAsync(cancellationToken);
        }

        store.Activations.AddRange(fresh);
        store.TranscriptFaults.AddRange(faults);

        if (cursor is null)
        {
            cursor = new IngestedTranscript { Path = path, Offset = readTo, Lines = lines };
            known.Cursors[path] = cursor;
            store.IngestedTranscripts.Add(cursor);
        }
        else
        {
            cursor.Offset = readTo;
            cursor.Lines = lines;
        }

        // One save per transcript. The activations, the faults and the cursor land together or not
        // at all, so no file is ever half ingested, and the screen fills while the first pass runs
        // rather than only at the end of it.
        await store.SaveChangesAsync(cancellationToken);
        known.Counted.UnionWith(firstSeenHere);

        return new TranscriptRead(true, fresh.Count);
    }

    private TranscriptFault Fault(string path, long line, string reason) => new()
    {
        Path = path,
        Line = line,
        Reason = reason,
        NoticedUtc = clock.GetUtcNow(),
    };

    /// <summary>
    /// Records that a file would not open, replacing the standing fault rather than stacking one up
    /// per pass: the cursor never moves past such a file, so every pass meets it again.
    /// </summary>
    private static async Task RefuseAsync(
        TelemetryDbContext store,
        Known known,
        TranscriptFault fault,
        CancellationToken cancellationToken)
    {
        if (!known.Unreadable.Add(fault.Path))
        {
            await store.TranscriptFaults
                .Where(f => f.Path == fault.Path && f.Line == TranscriptFault.WholeFile)
                .ExecuteDeleteAsync(cancellationToken);
        }

        store.TranscriptFaults.Add(fault);
        await store.SaveChangesAsync(cancellationToken);
    }
}
