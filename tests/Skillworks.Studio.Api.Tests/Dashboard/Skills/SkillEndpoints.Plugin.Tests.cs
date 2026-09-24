using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Dashboard.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Lists_every_skill_the_skillworks_Plugin_holds_from_this_repo_s_Marketplace()
    {
        var marketplace = Path.Combine(StudioHost.RepositoryRoot(), "plugins");
        var held = Directory.EnumerateDirectories(Path.Combine(marketplace, "skillworks", "skills"))
            .Select(skill => "skillworks:" + Path.GetFileName(skill))
            .Order(StringComparer.Ordinal);
        using var studio = new StudioHost(marketplace);

        var answer = await studio.SkillAnswer();

        Assert.Equal(held, answer.Head.PluginSkills.Order(StringComparer.Ordinal));
        Assert.Contains("skillworks:spec-loop", answer.Head.PluginSkills);
    }
}
