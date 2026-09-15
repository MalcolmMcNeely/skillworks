export function Keys<T extends string>({
  label,
  pressed,
  options,
  onPress,
}: {
  label: string;
  pressed: T | null;
  options: readonly { key: T; glyph?: string; word: string }[];
  onPress: (key: T) => void;
}) {
  return (
    <div className="keys" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          className="key"
          aria-pressed={pressed === option.key}
          onClick={() => onPress(option.key)}
        >
          {option.glyph !== undefined && <span aria-hidden="true">{option.glyph} </span>}
          {option.word}
        </button>
      ))}
    </div>
  );
}
