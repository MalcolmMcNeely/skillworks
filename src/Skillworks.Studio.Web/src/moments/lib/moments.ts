// UTC, because the filter counts whole UTC days and a local time can fall outside the day asked.
export function describeMoment(recorded: string): string {
  const moment = new Date(recorded);

  if (Number.isNaN(moment.getTime())) {
    return recorded;
  }

  return `${moment.toISOString().slice(0, 19).replace('T', ' ')} UTC`;
}
