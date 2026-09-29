using Skillworks.Core.Tests.Shared.Stores.TraceStore;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string CalledToolSpan = "a21c0a9e00000001";

    private const string ApprovalSpan = "a21c0a9e00000002";

    private const string ExecutedSpan = "a21c0a9e00000003";

    private const string OutputUse = "toolu_output";

    [Fact]
    public async Task Gives_a_tool_call_the_output_its_span_carries()
    {
        using var studio = new StudioHost();

        await CalledFor(studio, "Bash");
        await studio.PushSpans(Morning, MainTrace, Called(new Dictionary<string, string> { ["output"] = "Build succeeded." }));

        var call = await OnlyToolIn(studio);

        Assert.Equal("Build succeeded.", call.Output);
    }

    [Fact]
    public async Task Gives_a_read_the_content_of_the_file_it_read_as_its_output()
    {
        using var studio = new StudioHost();

        await CalledFor(studio, "Read");
        await studio.PushSpans(Morning, MainTrace, Called(new Dictionary<string, string> { ["content"] = "namespace Skillworks;" }));

        var call = await OnlyToolIn(studio);

        Assert.Equal("namespace Skillworks;", call.Output);
    }

    [Fact]
    public async Task Gives_an_edit_the_diff_its_span_carries()
    {
        using var studio = new StudioHost();
        const string diff = "@@ -1 +1 @@\n-var now = DateTime.UtcNow;\n+var now = clock.GetUtcNow();";

        await CalledFor(studio, "Edit");
        await studio.PushSpans(Morning, MainTrace, Called(new Dictionary<string, string> { ["diff"] = diff }));

        var call = await OnlyToolIn(studio);

        Assert.Equal(diff, call.Diff);
    }

    [Fact]
    public async Task Gives_a_tool_call_whose_output_was_withheld_no_output()
    {
        using var studio = new StudioHost();

        await CalledFor(studio, "Bash");
        await studio.PushSpans(Morning, MainTrace, Called(new Dictionary<string, string> { ["output"] = SessionEvent.Withheld }));

        var call = await OnlyToolIn(studio);

        Assert.Equal((true, null), (call.Traced, call.Output));
    }

    [Fact]
    public async Task Gives_a_tool_call_how_long_it_waited_for_approval()
    {
        using var studio = new StudioHost();

        await CalledFor(studio, "Bash");
        await studio.PushSpans(
            Morning,
            MainTrace,
            Called(),
            new("claude_code.tool.blocked_on_user", At(Yesterday, "09:00:01"), At(Yesterday, "09:00:04"), ApprovalSpan, CalledToolSpan, ToolUse: OutputUse));

        var call = await OnlyToolIn(studio);

        Assert.Equal(3_000L, call.WaitedMs);
    }

    [Fact]
    public async Task Gives_a_tool_call_how_long_it_ran()
    {
        using var studio = new StudioHost();

        await CalledFor(studio, "Bash");
        await studio.PushSpans(
            Morning,
            MainTrace,
            Called(),
            new("claude_code.tool.execution", At(Yesterday, "09:00:01"), At(Yesterday, "09:00:05"), ExecutedSpan, CalledToolSpan, ToolUse: OutputUse));

        var call = await OnlyToolIn(studio);

        Assert.Equal(4_000L, call.RanMs);
    }

    [Fact]
    public async Task Gives_a_tool_call_that_asked_no_one_no_wait()
    {
        using var studio = new StudioHost();

        await CalledFor(studio, "Bash");
        await studio.PushSpans(Morning, MainTrace, Called());

        var call = await OnlyToolIn(studio);

        Assert.Equal((true, null), (call.Traced, call.WaitedMs));
    }

    [Fact]
    public async Task Leaves_a_tool_calls_output_wait_and_running_time_not_known_in_a_session_with_no_spans()
    {
        using var studio = new StudioHost();

        await CalledFor(studio, "Bash");

        var call = await OnlyToolIn(studio);

        Assert.Equal((false, null, null, null, null), (call.Traced, call.Output, call.Diff, call.WaitedMs, call.RanMs));
    }

    private static RecordedSpan Called(IReadOnlyDictionary<string, string>? output = null) =>
        new("claude_code.tool", At(Yesterday, "09:00:00"), At(Yesterday, "09:00:05"), CalledToolSpan, ToolUse: OutputUse, Output: output);

    private static Task CalledFor(StudioHost studio, string tool) =>
        CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), tool, 5_000, OutputUse));
}
