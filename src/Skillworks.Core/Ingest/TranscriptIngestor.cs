using Microsoft.EntityFrameworkCore;
using Skillworks.Core.Activations;
using Skillworks.Core.Ingest.Parsing;
using Skillworks.Core.Spend;
using Skillworks.Core.TranscriptStore;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Ingest;

public sealed class TranscriptIngestor(
    TranscriptLocator locator,
    RepositoryNames repositories,
    IDbContextFactory<TranscriptStoreDbContext> contexts,
    TimeProvider clock)
{
    private readonly record struct TranscriptRead(bool HadNewContent, int ActivationsAdded);

    private sealed record Known(
        Dictionary<string, IngestedTranscript> Cursors,
        HashSet<string> Counted,
        HashSet<string> Charged,
        HashSet<string> Unreadable);

    public async Task<IngestPass> RunAsync(
        bool full,
        Action<IngestProgress> progress,
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        if (full)
        {
            await store.Activations.ExecuteDeleteAsync(cancellationToken);
            await store.Turns.ExecuteDeleteAsync(cancellationToken);
            await store.IngestedTranscripts.ExecuteDeleteAsync(cancellationToken);
            await store.TranscriptFaults.ExecuteDeleteAsync(cancellationToken);
        }

        var known = new Known(
            await store.IngestedTranscripts.ToDictionaryAsync(t => t.Path, cancellationToken),
            await store.Activations.Select(a => a.ToolUseId).ToHashSetAsync(cancellationToken),
            await store.Turns.Select(t => t.RequestId).ToHashSetAsync(cancellationToken),
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
        TranscriptStoreDbContext store,
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

        // Shorter than we left it means the file was replaced, not appended to.
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
        var turns = new List<Turn>();
        var faults = new List<TranscriptFault>();
        var firstSeenHere = new HashSet<string>();
        var chargedHere = new HashSet<string>();
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

                // Every record of a request repeats its whole usage, so the first one wins.
                if (reading.Turn is { } turn &&
                    !known.Charged.Contains(turn.RequestId) &&
                    chargedHere.Add(turn.RequestId))
                {
                    turns.Add(turn);
                }
            }
        }
        catch (Exception failure) when (failure is not OperationCanceledException)
        {
            // The file is left exactly as it was, and one transcript that will not open must not cost the others.
            await RefuseAsync(store, known, Fault(path, TranscriptFault.WholeFile, failure.Message), cancellationToken);

            return default;
        }

        var opened = known.Unreadable.Remove(path);

        if (restarted)
        {
            // Every line is read again, so the old contents' faults would collide with this pass's.
            await store.TranscriptFaults.Where(f => f.Path == path).ExecuteDeleteAsync(cancellationToken);
        }
        else if (opened)
        {
            // Only "would not open" goes: lines lost earlier are never re-read, so dropping them undercounts for good.
            await store.TranscriptFaults
                .Where(f => f.Path == path && f.Line == TranscriptFault.WholeFile)
                .ExecuteDeleteAsync(cancellationToken);
        }

        store.Activations.AddRange(fresh);
        store.Turns.AddRange(turns);
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

        // One save per transcript, so no file is half ingested and the screen fills while the first pass runs.
        await store.SaveChangesAsync(cancellationToken);
        known.Counted.UnionWith(firstSeenHere);
        known.Charged.UnionWith(chargedHere);

        return new TranscriptRead(true, fresh.Count);
    }

    private TranscriptFault Fault(string path, long line, string reason) => new()
    {
        Path = path,
        Line = line,
        Reason = reason,
        NoticedUtc = clock.GetUtcNow(),
    };

    // Replaces rather than adds: the cursor never passes a file that would not open, so every pass meets it.
    private static async Task RefuseAsync(
        TranscriptStoreDbContext store,
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
