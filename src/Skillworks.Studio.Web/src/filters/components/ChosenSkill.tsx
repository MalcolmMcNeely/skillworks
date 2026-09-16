// A Skill reaches a list by link, not by a picker, so the page honouring one must show it and clear it.
export function ChosenSkill({ skill, onClear }: { skill: string; onClear: () => void }) {
  if (skill === '') {
    return null;
  }

  return (
    <p className="chosen-skill">
      <span className="micro">Skill</span>
      <span className="chosen-skill-name">{skill}</span>
      <button type="button" onClick={onClear}>
        Clear
      </button>
    </p>
  );
}
