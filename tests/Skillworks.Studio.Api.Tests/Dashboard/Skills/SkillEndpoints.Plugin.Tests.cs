using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Dashboard.Skills;

public sealed partial class SkillEndpointsTests
{
    [Fact]
    public async Task Lists_every_skill_the_skillworks_Plugin_holds_from_its_Marketplace()
    {
        var marketplace = Path.Combine(AppContext.BaseDirectory, "Dashboard", "Skills", "PluginMarketplace");
        using var studio = new StudioHost(marketplace);

        var answer = await studio.SkillAnswer();

        Assert.Equal(["skillworks:grilling", "skillworks:spec-loop"], answer.Head.PluginSkills.Order(StringComparer.Ordinal));
    }
}
