using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    private const string BuildParameters =
        """{"bash_command":"dotnet","full_command":"dotnet build --no-restore","description":"Build the solution"}""";

    [Fact]
    public async Task Gives_a_bash_call_its_whole_command_and_its_description_from_its_parameters()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000")) with
        {
            ToolParameters = BuildParameters,
            ToolInput = """{"command":"dotnet build","description":"Build"}""",
        });

        var call = await OnlyToolIn(studio);

        Assert.Equal(("dotnet build --no-restore", "Build the solution"), (call.Command, call.Description));
    }

    [Fact]
    public async Task Takes_a_bash_calls_command_and_description_from_its_input_where_it_named_no_parameters()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000")) with
        {
            ToolInput = """{"command":"npm test","description":"Run the tests"}""",
        });

        var call = await OnlyToolIn(studio);

        Assert.Equal(("npm test", "Run the tests"), (call.Command, call.Description));
    }

    [Fact]
    public async Task Gives_a_tool_call_its_input_and_its_parameters_as_claude_code_sent_them()
    {
        using var studio = new StudioHost();
        const string input = """{"skill":"skillworks:tdd","args":"494"}""";
        const string parameters = """{"skill_name":"skillworks:tdd"}""";

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), "Skill") with
        {
            ToolInput = input,
            ToolParameters = parameters,
        });

        var call = await OnlyToolIn(studio);

        Assert.Equal(("Skill", input, parameters), (call.Tool, call.Input, call.Parameters));
    }

    [Fact]
    public async Task Gives_a_tool_call_the_size_of_its_whole_result()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000"), "Read") with { ResultBytes = "48213" });

        var call = await OnlyToolIn(studio);

        Assert.Equal(48_213L, call.ResultBytes);
    }

    [Theory]
    [InlineData("config")]
    [InlineData("user_temporary")]
    [InlineData("user_permanent")]
    [InlineData("hook")]
    public async Task Gives_a_tool_call_who_allowed_it(string allowedBy)
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000")) with { AllowedBy = allowedBy });

        var call = await OnlyToolIn(studio);

        Assert.Equal(allowedBy, call.AllowedBy);
    }

    [Fact]
    public async Task Gives_a_tool_call_that_passed_no_error()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000")));

        var call = await OnlyToolIn(studio);

        Assert.Equal((true, null), (call.Passed, call.Error));
    }

    [Fact]
    public async Task Gives_a_failed_tool_call_its_error_text()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolFailed(Morning, At(Yesterday, "09:00:05.000")) with
        {
            Error = "Exit code 1: error CS0103: The name 'clock' does not exist",
        });

        var call = await OnlyToolIn(studio);

        Assert.Equal((false, "Exit code 1: error CS0103: The name 'clock' does not exist"), (call.Passed, call.Error));
    }

    [Fact]
    public async Task Gives_a_failed_tool_call_its_error_kind_where_claude_code_sent_no_text()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolFailed(Morning, At(Yesterday, "09:00:05.000")));

        var call = await OnlyToolIn(studio);

        Assert.Equal((false, "ShellError"), (call.Passed, call.Error));
    }

    [Fact]
    public async Task Gives_a_bash_call_whose_command_was_withheld_no_command_and_the_size_of_its_input()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000")) with
        {
            ToolInput = SessionEvent.Withheld,
            InputBytes = "812",
        });

        var call = await OnlyToolIn(studio);

        Assert.Equal((null, null, 812L), (call.Command, call.Input, call.InputBytes));
    }

    [Fact]
    public async Task Gives_a_bash_call_sent_with_the_tool_details_off_no_command_and_the_size_of_its_input()
    {
        using var studio = new StudioHost();

        await CalledWith(studio, SessionEvent.ToolRan(Morning, At(Yesterday, "09:00:05.000")) with { InputBytes = "96" });

        var call = await OnlyToolIn(studio);

        Assert.Equal((null, null, 96L), (call.Command, call.Input, call.InputBytes));
    }

    private static Task CalledWith(StudioHost studio, SessionEvent call) =>
        studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build"), call);

    private static async Task<ToolDetailsRow> OnlyToolIn(StudioHost studio)
    {
        var answer = await studio.StepAnswer(Morning);
        var call = Assert.Single(answer.Steps, step => step.Kind == "tool");

        return answer.Tools[call.Id];
    }
}
