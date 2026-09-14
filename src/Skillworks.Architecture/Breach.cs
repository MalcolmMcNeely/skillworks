namespace Skillworks.Architecture;

public sealed record Breach(string Rule, string Path, string Message)
{
    public override string ToString() => $"{Rule} at {Path}: {Message}";
}
