// Not part of the Filter: it names one run and narrows no other list, so it stays out of the address bar and a reload clears it.
export function Lookup({ text, onChange }: { text: string; onChange: (text: string) => void }) {
  return (
    <label className="lookup">
      <span className="micro">Lookup</span>
      <input
        type="text"
        value={text}
        placeholder="Session id"
        autoComplete="off"
        spellCheck={false}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
