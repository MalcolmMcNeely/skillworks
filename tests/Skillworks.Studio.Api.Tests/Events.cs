using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json.Nodes;

namespace Skillworks.Studio.Api.Tests;

/// <summary>One skill_activated event, as Claude Code would have emitted it.</summary>
/// <param name="At">An instant in ISO 8601, so a fixture reads as a moment rather than as a number.</param>
public sealed record Event(
    string Skill,
    string At,
    string? Trigger = null,
    string? Source = null,
    string? Plugin = null,
    string? Marketplace = null);

/// <summary>
/// The events store, stubbed where Studio speaks to it and nowhere else: at HTTP. The real query
/// is built, sent and parsed against these answers, so the whole Loki path is under test and no
/// container has to be running.
/// </summary>
public sealed class Events : HttpMessageHandler
{
    private readonly Func<HttpResponseMessage> _answer;

    private Events(Func<HttpResponseMessage> answer) => _answer = answer;

    /// <summary>The last thing Studio asked for, so a test can assert the query as well as the answer.</summary>
    public Uri? LastAsked { get; private set; }

    /// <summary>A store that is up and holds these events, in the shape Loki hands them back.</summary>
    public static Events Holding(params Event[] events) => Answering(Streams(events));

    /// <summary>A store that is up and answering, with a body of its own choosing.</summary>
    public static Events Answering(string body) => new(() => new HttpResponseMessage(HttpStatusCode.OK)
    {
        Content = new StringContent(body, Encoding.UTF8, "application/json"),
    });

    /// <summary>A container that is not running, which is the ordinary way this store is absent.</summary>
    public static Events Down() => new(() => throw new HttpRequestException("connection refused"));

    /// <summary>A store that is up and unhappy, which must not read as a store that is quiet.</summary>
    public static Events Failing(HttpStatusCode status) => new(() => new HttpResponseMessage(status));

    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        LastAsked = request.RequestUri;

        return Task.FromResult(_answer());
    }

    /// <summary>
    /// Loki's streams answer. The attributes ride as the third part of each entry, which is where
    /// its OTLP ingest puts a log record's attributes, and their dots become underscores on the way.
    /// </summary>
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

    /// <summary>An attribute Claude Code did not emit is left out, not written as an empty one.</summary>
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
