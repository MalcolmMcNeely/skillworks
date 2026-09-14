using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Comments;

internal sealed record CommentRules(bool DocComments)
{
    public const string RelativePath = ".claude/rules/comments.md";

    public static CommentRules Read(RulesFile file) => new(file.RequireTrueOrFalse("doc-comments"));
}
