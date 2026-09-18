using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed partial class SessionEndpointsTests
{
    [Fact]
    public async Task Names_a_session_by_the_title_Claude_Code_wrote_for_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build before the demo"),
            SessionEvent.Titled(Morning, At(Yesterday, "09:00:30.000"), "Fixing the failing build"));

        // The title is the one a reader recognises, so it wins over the words that led to it.
        Assert.Equal("Fixing the failing build", Assert.Single(await studio.SessionsIn()).Name);
    }

    [Fact]
    public async Task Names_a_session_with_no_title_by_its_first_prompt()
    {
        using var studio = new StudioHost();

        await studio.Push(
            SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build before the demo"),
            SessionEvent.Prompted(Morning, At(Yesterday, "09:30:00.000"), "Now push it"));

        Assert.Equal("Fix the build before the demo", Assert.Single(await studio.SessionsIn()).Name);
    }

    [Fact]
    public async Task Names_a_session_with_neither_by_its_repository_and_the_time_it_started()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SessionEvent(Morning, "tool_result", At(Yesterday, "09:00:00.000"))
            {
                Owner = "malcolmania",
                RepositoryName = "skillworks",
            });

        // Never empty, or a row would be unreadable in the one column that says which run it is.
        Assert.Equal($"malcolmania/skillworks {Written(Yesterday)} 09:00", Assert.Single(await studio.SessionsIn()).Name);
    }

    [Fact]
    public async Task Names_a_session_with_neither_and_no_repository_by_the_time_it_started()
    {
        using var studio = new StudioHost();

        await studio.Push(new SessionEvent(Morning, "tool_result", At(Yesterday, "09:00:00.000")));

        Assert.Equal($"{Written(Yesterday)} 09:00", Assert.Single(await studio.SessionsIn()).Name);
    }

    [Fact]
    public async Task Falls_past_a_prompt_whose_words_were_withheld()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SessionEvent(Morning, "user_prompt", At(Yesterday, "09:00:00.000"))
            {
                Prompt = SessionEvent.Withheld,
                Owner = "acme",
                RepositoryName = "xi",
            });

        // Claude Code withheld the words, so the row says where and when instead of the placeholder.
        Assert.Equal($"acme/xi {Written(Yesterday)} 09:00", Assert.Single(await studio.SessionsIn()).Name);
    }

    [Fact]
    public async Task Shows_the_opening_words_of_a_long_prompt()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), new string('a', 400)));

        var name = Assert.Single(await studio.SessionsIn()).Name;

        // A whole prompt is a page of text, and a table row shows one line of it.
        Assert.Equal(new string('a', 120) + "…", name);
    }

    [Fact]
    public async Task Reads_a_prompt_written_over_several_lines_as_one_line()
    {
        using var studio = new StudioHost();

        await studio.Push(SessionEvent.Prompted(Morning, At(Yesterday, "09:00:00.000"), "Fix the build\nthen push it"));

        Assert.Equal("Fix the build then push it", Assert.Single(await studio.SessionsIn()).Name);
    }
}
