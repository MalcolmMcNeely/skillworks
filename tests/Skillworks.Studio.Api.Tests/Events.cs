using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json.Nodes;

namespace Skillworks.Studio.Api.Tests;

public sealed record Event(
    string Skill,
    string At,
    string? Trigger = null,
    string? Source = null,
    string? Plugin = null,
    string? Marketplace = null);

public sealed class Events : HttpMessageHandler
{
    private readonly Func<HttpResponseMessage> _answer;

    private Events(Func<HttpResponseMessage> answer) => _answer = answer;

    public Uri? LastAsked { get; private set; }

    public static Events Holding(params Event[] events) => Answering(Streams(events));

    public static Events Answering(string body) => new(() => new HttpResponseMessage(HttpStatusCode.OK)
    {
        Content = new StringContent(body, Encoding.UTF8, "application/json"),
    });

    public static Events Down() => new(() => throw new HttpRequestException("connection refused"));

    public static Events Failing(HttpStatusCode status) => new(() => new HttpResponseMessage(status));

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        LastAsked = request.RequestUri;

        return Task.FromResult(_answer());
    }

    // Loki's OTLP ingest puts a record's attributes third in each entry, with dots turned to underscores.
    private static string Streams(IReadOnlyList<Event> events)
    {
        var values = new JsonArray();

        foreach (var recorded in events)
        {
            var attributes = new JsonObject
            {
                ["event_name"] = "skill_activated",
                ["skill_name"] = recorded.Skill,
            };

            Add(attributes, "invocation_trigger", recorded.Trigger);
            Add(attributes, "skill_source", recorded.Source);
            Add(attributes, "plugin_name", recorded.Plugin);
            Add(attributes, "marketplace_name", recorded.Marketplace);

            values.Add(new JsonArray(
                JsonValue.Create(Nanoseconds(recorded.At)),
                JsonValue.Create("claude_code.skill_activated"),
                attributes));
        }

        return new JsonObject
        {
            ["status"] = "success",
            ["data"] = new JsonObject
            {
                ["resultType"] = "streams",
                ["result"] = new JsonArray(new JsonObject
                {
                    ["stream"] = new JsonObject { ["service_name"] = "claude-code" },
                    ["values"] = values,
                }),
            },
        }.ToJsonString();
    }

    private static void Add(JsonObject attributes, string name, string? value)
    {
        if (value is not null)
        {
            attributes[name] = value;
        }
    }

    private static string Nanoseconds(string at) =>
        (DateTimeOffset.Parse(at, CultureInfo.InvariantCulture).ToUnixTimeMilliseconds() * 1_000_000)
        .ToString(CultureInfo.InvariantCulture);
}
