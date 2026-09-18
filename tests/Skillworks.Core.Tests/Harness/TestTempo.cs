using System.Globalization;
using System.Net.Http.Headers;
using System.Text.Json.Nodes;
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;
using Skillworks.AppHost;

namespace Skillworks.Core.Tests.Harness;

public static class TestTempo
{
    private const int HttpPort = 3200;

    private const int OtlpPort = 4318;

    private const string ClaudeCodeVersion = "2.1.268";

    // One per run, as Tempo starts slowly; on the thread pool, so a waiting constructor cannot deadlock xUnit.
    private static readonly Lazy<IContainer> Started = new(() => Task.Run(StartAsync).GetAwaiter().GetResult());

    private static readonly HttpClient Client = new();

    public static Uri Address => Mapped(HttpPort);

    public static async Task PushAsync(string tenant, string session, IReadOnlyList<JsonObject> spans)
    {
        await SendAsync(new Uri(Mapped(OtlpPort), "v1/traces"), tenant, Traces(spans));

        // Tempo searches what has reached its store, not what it is still holding.
        await FlushAsync();
        await SearchableAsync(tenant, session, spans);
    }

    private static async Task<IContainer> StartAsync()
    {
        var configuration = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Harness", "tempo.yaml"));

        // Not disposed: Testcontainers' reaper removes it when the test run ends.
        var container = new ContainerBuilder($"{TempoImage.Name}:{TempoImage.Tag}")
            .WithResourceMapping(configuration, "/etc/tempo/config.yaml")
            .WithCommand("-config.file=/etc/tempo/config.yaml")
            .WithPortBinding(HttpPort, assignRandomHostPort: true)
            .WithPortBinding(OtlpPort, assignRandomHostPort: true)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilHttpRequestIsSucceeded(ready => ready.ForPort(HttpPort).ForPath("/ready")))
            .Build();

        await container.StartAsync();

        return container;
    }

    private static Uri Mapped(int port) =>
        new UriBuilder(Uri.UriSchemeHttp, Started.Value.Hostname, Started.Value.GetMappedPublicPort(port)).Uri;

    private static async Task SendAsync(Uri route, string tenant, JsonObject body)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, route)
        {
            Content = new StringContent(body.ToJsonString(), new MediaTypeHeaderValue("application/json")),
        };

        request.Headers.Add("X-Scope-OrgID", tenant);

        using var response = await Client.SendAsync(request);

        // Tempo names the span it refused only in the body.
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException(
                $"Tempo refused the spans with {(int)response.StatusCode}: {await response.Content.ReadAsStringAsync()}");
        }
    }

    private static async Task FlushAsync()
    {
        using var response = await Client.PostAsync(new Uri(Address, "flush"), null);

        response.EnsureSuccessStatusCode();
    }

    // Asked trace by trace, because a second push into a session already searchable would otherwise pass at once.
    private static async Task SearchableAsync(string tenant, string session, IReadOnlyList<JsonObject> spans)
    {
        var pushed = spans.Select(span => Shortened((string)span["traceId"]!)).ToHashSet(StringComparer.Ordinal);
        var giveUp = DateTime.UtcNow.AddSeconds(30);
        var query = Uri.EscapeDataString($"{{ span.session.id = \"{session}\" }}");

        // A store that keeps the ordinary limit refuses a window wider than a week, so it is cut to the spans.
        var route = new Uri(Address, $"api/search?q={query}&{Window(spans)}&limit=1000");

        while (DateTime.UtcNow < giveUp)
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, route);

            request.Headers.Add("X-Scope-OrgID", tenant);

            using var response = await Client.SendAsync(request);
            var answered = await response.Content.ReadAsStringAsync();

            // Tempo says why it refused a window only in the body.
            if (!response.IsSuccessStatusCode)
            {
                throw new InvalidOperationException($"Tempo refused {route} with {(int)response.StatusCode}: {answered}");
            }

            var found = JsonNode.Parse(answered)?["traces"] as JsonArray ?? [];

            if (pushed.IsSubsetOf(found.Select(trace => Shortened((string)trace!["traceID"]!))))
            {
                return;
            }

            await Task.Delay(200);
        }

        throw new InvalidOperationException($"Tempo never made the spans of {session} searchable.");
    }

    // Tempo picks the blocks to read by when the spans reached it, so the window covers now as well as the spans.
    private static string Window(IReadOnlyList<JsonObject> spans)
    {
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var first = spans.Min(span => Seconds(span, "startTimeUnixNano"));
        var last = spans.Max(span => Seconds(span, "endTimeUnixNano"));

        return $"start={Math.Min(first, now)}&end={Math.Max(last, now) + 60}";
    }

    private static long Seconds(JsonObject span, string field) =>
        long.Parse((string)span[field]!, CultureInfo.InvariantCulture) / 1_000_000_000;

    // Tempo answers with a trace id stripped of its leading zeroes.
    private static string Shortened(string traceId) => traceId.TrimStart('0');

    private static JsonObject Traces(IReadOnlyList<JsonObject> spans) => new()
    {
        ["resourceSpans"] = new JsonArray(new JsonObject
        {
            ["resource"] = new JsonObject
            {
                ["attributes"] = new JsonArray(
                    Attribute("service.name", "claude-code"),
                    Attribute("service.version", ClaudeCodeVersion)),
            },
            ["scopeSpans"] = new JsonArray(new JsonObject
            {
                ["scope"] = new JsonObject { ["name"] = "com.anthropic.claude_code", ["version"] = ClaudeCodeVersion },
                ["spans"] = new JsonArray([.. spans]),
            }),
        }),
    };

    private static JsonObject Attribute(string key, string value) =>
        new() { ["key"] = key, ["value"] = new JsonObject { ["stringValue"] = value } };
}
