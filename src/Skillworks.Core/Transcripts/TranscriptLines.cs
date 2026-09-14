using System.Text;

namespace Skillworks.Core.Transcripts;

public readonly record struct TranscriptLine(string Text, long EndOffset);

public static class TranscriptLines
{
    private const int BufferSize = 64 * 1024;

    // A last line with no newline is still being written, so it waits for the next pass.
    public static IEnumerable<TranscriptLine> From(string path, long offset)
    {
        using var file = new FileStream(
            path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);

        if (offset >= file.Length)
        {
            yield break;
        }

        file.Seek(offset, SeekOrigin.Begin);

        var buffer = new byte[BufferSize];
        var line = new MemoryStream(BufferSize);
        var position = offset;
        int read;

        while ((read = file.Read(buffer, 0, buffer.Length)) > 0)
        {
            for (var i = 0; i < read; i++)
            {
                position++;

                if (buffer[i] != (byte)'\n')
                {
                    line.WriteByte(buffer[i]);
                    continue;
                }

                yield return new TranscriptLine(Decode(line), position);
                line.SetLength(0);
            }
        }
    }

    private static string Decode(MemoryStream line) =>
        Encoding.UTF8.GetString(line.GetBuffer(), 0, (int)line.Length).TrimEnd('\r');
}
