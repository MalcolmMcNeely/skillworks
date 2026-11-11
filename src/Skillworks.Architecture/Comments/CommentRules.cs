using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Comments;

internal sealed record CommentRules(DocCommentFiles DocComments)
{
    public const string RelativePath = "docs/skillworks/rules/comments.md";

    public static CommentRules Read(RulesFile file) => new(file.RequireOneOf<DocCommentFiles>("doc-comments"));
}
