using System.Text.Json;
using Microsoft.AspNetCore.Http.Json;
using Microsoft.Extensions.Options;
using Skillworks.Core.Arriving;

namespace Skillworks.Studio.Api.Arriving;

// Flushed after every line, so a day is on screen as soon as it is read, not when the last day is.
public sealed class ArrivingAnswer(IAsyncEnumerable<ArrivingLine> lines) : IResult
{
    private static readonly byte[] LineEnd = "\n"u8.ToArray();

    public async Task ExecuteAsync(HttpContext http)
    {
        var json = http.RequestServices.GetRequiredService<IOptions<JsonOptions>>().Value.SerializerOptions;
        var body = http.Response.Body;

        http.Response.ContentType = "application/x-ndjson";

        await foreach (var line in lines.WithCancellation(http.RequestAborted))
        {
            // As its own type, as the base type would write only the kind.
            await JsonSerializer.SerializeAsync(body, line, line.GetType(), json, http.RequestAborted);
            await body.WriteAsync(LineEnd, http.RequestAborted);
            await body.FlushAsync(http.RequestAborted);
        }
    }
}
