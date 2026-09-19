using System.Globalization;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions;

// The one column that says which run a row is, so it is never empty.
public static class SessionName
{
    // A prompt is a page of text and a row is a line, so only the opening words go on screen.
    private const int Opening = 120;

    public static string Of(string? title, string? prompt, string? repository, DateTimeOffset started) =>
        Words(title) ?? Words(prompt) ?? Placed(repository, started);

    private static string? Words(string? said)
    {
        if (said is null || said == EventAttributes.Withheld)
        {
            return null;
        }

        // A row shows one line, and a prompt runs over many.
        var line = string.Join(' ', said.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));

        return line.Length switch
        {
            0 => null,
            > Opening => line[..Opening] + '…',
            _ => line,
        };
    }

    private static string Placed(string? repository, DateTimeOffset started)
    {
        var when = started.UtcDateTime.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture);

        return repository is null ? when : $"{repository} {when}";
    }
}
