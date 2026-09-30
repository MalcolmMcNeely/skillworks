using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows.Details;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Theory]
    [InlineData("config")]
    [InlineData("hook")]
    [InlineData("user_reject")]
    [InlineData("user_abort")]
    public async Task Gives_a_refused_tool_call_who_refused_it(string refusedBy)
    {
        using var studio = new StudioHost();

        await RefusedWith(studio, SessionEvent.Refused(Morning, At(Yesterday, "09:00:05.000")) with { DecisionSource = refusedBy });

        var refusal = await OnlyRefusalIn(studio);

        Assert.Equal(refusedBy, refusal.RefusedBy);
    }

    [Fact]
    public async Task Gives_a_refused_bash_call_the_tool_and_the_command_it_asked_with()
    {
        using var studio = new StudioHost();

        await RefusedWith(studio, SessionEvent.Refused(Morning, At(Yesterday, "09:00:05.000")) with
        {
            ToolParameters = """{"bash_command":"rm","full_command":"rm -rf bin","description":"Clear the build output"}""",
        });

        var refusal = await OnlyRefusalIn(studio);

        Assert.Equal(("Bash", "rm -rf bin", "Clear the build output"), (refusal.Tool, refusal.Command, refusal.Description));
    }

    [Fact]
    public async Task Gives_a_refused_tool_call_its_input_as_claude_code_sent_it()
    {
        using var studio = new StudioHost();
        const string input = """{"file_path":"src/Program.cs"}""";

        await RefusedWith(studio, SessionEvent.Refused(Morning, At(Yesterday, "09:00:05.000"), "Edit") with { ToolInput = input });

        var refusal = await OnlyRefusalIn(studio);

        Assert.Equal(("Edit", input), (refusal.Tool, refusal.Input));
    }

    private static Task RefusedWith(StudioHost studio, SessionEvent refused) =>
        studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Clear the build"), refused);

    private static async Task<RefusalDetailsRow> OnlyRefusalIn(StudioHost studio)
    {
        var answer = await studio.StepAnswer(Morning);
        var refused = Assert.Single(answer.Steps, step => step.Kind == "refused");

        return answer.Refusals[refused.Id];
    }
}
