namespace Skillworks.AppHost;

// The API tests start this image too, so the queries they prove are the queries this Loki answers.
public static class LokiImage
{
    public const string Name = "grafana/loki";

    public const string Tag = "3.5.9";
}
