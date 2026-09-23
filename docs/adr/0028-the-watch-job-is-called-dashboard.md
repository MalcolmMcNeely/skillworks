# The Watch job is called Dashboard

Studio's first job, and the page that does it, was called Watch, and the glossary listed Dashboard
as the word to avoid. Everyone knows what to expect from a page called Dashboard, and nobody knows
what to expect from one called Watch. So the job and its page are both called Dashboard now, and
Watch is the word to avoid. The name reaches the code as well as the screen, because the code speaks
the glossary: the `Watch` Slice becomes `Dashboard` in every project, in the namespaces, in the
`slices` list and in the front end, and the page moves from `/watch` to `/dashboard`.

Nobody uses Studio yet, so no bookmark needs keeping. `/watch` is not sent on to `/dashboard`, and
the older redirect that sent pre-address links on to Watch is deleted with it.

## Considered options

**Rename the page and keep the job called Watch.** Rejected. The Slices would stay `Watch` while the
screen said Dashboard, so the code would use a word the glossary no longer holds for that thing.

## Consequences

The jobs are no longer all verbs: Dashboard, Author, Test and Publish. ADR 0002 says "Studio is the
dashboard" and ADR 0017 names the `Watch` Slice. Both are history and stay as they were written.
