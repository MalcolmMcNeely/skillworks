using Skillworks.Architecture.Comments;
using Skillworks.Architecture.Contexts;
using Skillworks.Architecture.Placement;
using Skillworks.Architecture.RulesFiles;
using Skillworks.Architecture.Words;

namespace Skillworks.Architecture;

internal sealed record Rules(
    PlacementRules Placement,
    CommentRules Comments,
    WordRules Words,
    ContextRules Contexts,
    IReadOnlyList<Breach> Breaches)
{
    public static Rules Read(string root)
    {
        var placementFile = RulesFile.Load(root, PlacementRules.RelativePath);
        var commentsFile = RulesFile.Load(root, CommentRules.RelativePath);
        var wordsFile = RulesFile.Load(root, WordRules.RelativePath);
        var contextsFile = RulesFile.Load(root, ContextRules.RelativePath);

        var placement = PlacementRules.Read(placementFile);
        var comments = CommentRules.Read(commentsFile);
        var words = WordRules.Read(wordsFile);
        var contexts = ContextRules.Read(contextsFile);

        return new(
            placement,
            comments,
            words,
            contexts,
            [
                .. placementFile.Breaches,
                .. commentsFile.Breaches,
                .. wordsFile.Breaches,
                .. contextsFile.Breaches,
            ]);
    }
}
