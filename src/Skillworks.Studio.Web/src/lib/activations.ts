/**
 * Where one skill's firings are listed. The skill goes in the path rather than the filter, so a
 * reader who narrowed to nothing comes back to a table narrowed to nothing: writing it into the
 * filter would hand them a view they never asked for.
 */
export function activationsPath(search: string, skill: string): string {
  return `/skills/${encodeURIComponent(skill)}/activations${query(search)}`;
}

/** Where one firing is opened. */
export function activationPath(search: string, id: string): string {
  return `/activations/${encodeURIComponent(id)}${query(search)}`;
}

/** The way back to the skill table. */
export function skillsPath(search: string): string {
  return `/${query(search)}`;
}

/**
 * The address the reader is on, carried whole to the next one. Passed through rather than rebuilt
 * from the filter, because the sort is in there too and anything rebuilt from a part drops the rest.
 */
function query(search: string): string {
  return search === '' ? '' : `?${search}`;
}

/**
 * When a firing happened, in UTC. The filter counts whole UTC days, so a moment shown at the
 * reader's own clock could sit outside the day they asked about, which is worse than a label.
 */
export function describeMoment(recorded: string): string {
  const moment = new Date(recorded);

  if (Number.isNaN(moment.getTime())) {
    return recorded;
  }

  return `${moment.toISOString().slice(0, 19).replace('T', ' ')} UTC`;
}

/**
 * One thing a transcript either recorded or did not. A dash rather than an empty cell, so a fact
 * that is missing reads as missing rather than as a hole in the page.
 */
export function describeRecorded(value: string | null): string {
  return value === null || value === '' ? '—' : value;
}
