namespace Skillworks.Core.Activations;

// Always text: the reader judges the words an argument used, not the JSON shape they arrived in.
public sealed record ActivationArgument(string Name, string Value);
