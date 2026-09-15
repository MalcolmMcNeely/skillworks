// The skill goes in the path, not the filter, so going back does not narrow the table to it.
export function activationsPath(search: string, skill: string): string {
  return `/skills/${encodeURIComponent(skill)}/activations${query(search)}`;
}

export function activationPath(search: string, id: string): string {
  return `/activations/${encodeURIComponent(id)}${query(search)}`;
}

export function skillsPath(search: string): string {
  return `/${query(search)}`;
}

function query(search: string): string {
  return search === '' ? '' : `?${search}`;
}

// Words, not a dash, which would read as a fact about the firing rather than a gap in its event.
export function describeRecorded(value: string | null): string {
  return value === null || value === '' ? 'Not recorded' : value;
}
