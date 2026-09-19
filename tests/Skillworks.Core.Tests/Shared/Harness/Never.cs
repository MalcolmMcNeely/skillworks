namespace Skillworks.Core.Tests.Shared.Harness;

// A stand-in holds a read open with no wait of its own, so no machine clock decides when it ends.
public static class Never
{
    public static Task Answers(CancellationToken cancellationToken) =>
        new TaskCompletionSource().Task.WaitAsync(cancellationToken);
}
