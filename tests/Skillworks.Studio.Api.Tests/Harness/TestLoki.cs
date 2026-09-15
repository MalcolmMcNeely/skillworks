using System.Globalization;
using System.Net.Http.Headers;
using System.Text.Json.Nodes;
using DotNet.Testcontainers.Builders;
using Skillworks.AppHost;

namespace Skillworks.Studio.Api.Tests.Harness;

public static class TestLoki
{
    private const int Port = 3100;

    private const string ClaudeCodeVersion = "2.1.268";

    private const string Session = "0a9f1c2e-0000-4000-8000-000000000001";

    // One per run, as Loki starts slowly; on the thread pool, so a waiting constructor cannot deadlock xUnit.
    private static readonly Lazy<Uri> StartedAddress = new(() => Task.Run(StartAsync).GetAwaiter().GetResult());

    private static readonly HttpClient Client = new();

    // Shared across pushes, so no two events in a session share a sequence, as in Claude Code.
    private static long _sequence;

    public static Uri Address => StartedAddress.Value;

    public static async Task PushAsync(string tenant, IReadOnlyList<SkillActivated> events)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(Address, "otlp/v1/logs"))
        {
            // Without a charset: Loki's OTLP route refuses "application/json; charset=utf-8".
            Content = new StringContent(Logs(events).ToJsonString(), new MediaTypeHeaderValue("application/json")),
        };

        request.Headers.Add("X-Scope-OrgID", tenant);

        using var response = await Client.SendAsync(request);

        // Loki names the entry it refused only in the body.
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException(
                $"Loki refused the events with {(int)response.StatusCode}: {await response.Content.ReadAsStringAsync()}");
        }
    }

    private static async Task<Uri> StartAsync()
    {
        var configuration = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Harness", "loki.yaml"));

        // Not disposed: Testcontainers' reaper removes it when the test run ends.
        var container = new ContainerBuilder($"{LokiImage.Name}:{LokiImage.Tag}")
            .WithResourceMapping(configuration, "/etc/loki/test.yaml")
            .WithCommand("-config.file=/etc/loki/test.yaml")
            .WithPortBinding(Port, assignRandomHostPort: true)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilHttpRequestIsSucceeded(ready => ready.ForPort(Port).ForPath("/ready")))
            .Build();

        await container.StartAsync();

        return new UriBuilder(Uri.UriSchemeHttp, container.Hostname, container.GetMappedPublicPort(Port)).Uri;
    }

    private static JsonObject Logs(IReadOnlyList<SkillActivated> events) => new()
    {
        ["resourceLogs"] = new JsonArray(new JsonObject
        {
            ["resource"] = new JsonObject
            {
                ["attributes"] = Attributes([("service.name", "claude-code"), ("service.version", ClaudeCodeVersion)]),
            },
            ["scopeLogs"] = new JsonArray(new JsonObject
            {
                ["scope"] = new JsonObject { ["name"] = "com.anthropic.claude_code.events", ["version"] = ClaudeCodeVersion },
                ["logRecords"] = new JsonArray([.. events.Select(LogRecord)]),
            }),
        }),
    };

    private static JsonObject LogRecord(SkillActivated recorded)
    {
        var at = recorded.Moment;
        var sequence = recorded.Sequence ?? Interlocked.Increment(ref _sequence);
        var nanoseconds = ((at.UtcTicks - DateTimeOffset.UnixEpoch.UtcTicks) * 100).ToString(CultureInfo.InvariantCulture);

        return new JsonObject
        {
            ["timeUnixNano"] = nanoseconds,
            ["observedTimeUnixNano"] = nanoseconds,
            ["body"] = new JsonObject { ["stringValue"] = $"claude_code.{SkillActivated.EventName}" },
            ["attributes"] = Attributes(
            [
                ("user.id", "a68801ea0000400080000000000000001"),
                ("session.id", recorded.Session ?? Session),
                ("app.version", ClaudeCodeVersion),
                ("organization.id", "14451454-0000-4000-8000-000000000001"),
                ("user.account_uuid", "784e9f9a-0000-4000-8000-000000000001"),
                ("terminal.type", "windows-terminal"),
                ("event.name", SkillActivated.EventName),
                ("event.timestamp", at.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture)),
                ("event.sequence", sequence.ToString(CultureInfo.InvariantCulture)),
                ("prompt.id", "3b0537fa-0000-4000-8000-000000000001"),
                .. recorded.Attributes,
            ]),
        };
    }

    private static JsonArray Attributes(IEnumerable<(string Key, string? Value)> attributes) =>
    [
        .. attributes
            .Where(attribute => attribute.Value is not null)
            .Select(attribute => new JsonObject
            {
                ["key"] = attribute.Key,
                ["value"] = new JsonObject { ["stringValue"] = attribute.Value },
            })
    ];
}
