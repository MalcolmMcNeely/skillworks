# PROTOTYPE: the Lookup on the Sessions list

Throwaway. Nothing here builds or ships.

**The question:** what should a box on the Sessions list that takes a Session id look like?

**The verdict:** variant B. The box sits on the right, opposite the Repository picker. Part of an id
narrows the rows already read. A whole id that no row holds is asked of the stores, and the reader
opens a run only by picking its row, so an id that names no run never opens a page.

Variant A (Enter opens the run) lost because a mistyped id opens an empty page. Variant C (a palette
with a preview) lost because it cost more than B and showed nothing B does not.

The prototype's whole-id read found runs from the last seven days only, because the one-run read with
no span covers the lookback. The real Lookup reaches ninety days.

To run it, copy the three `.tsx` files back: `Sessions.tsx` to
`src/Skillworks.Studio.Web/src/sessions/routes/`, and the other two to
`src/Skillworks.Studio.Web/src/sessions/components/`. Then open `/sessions?variant=A`, `B` or `C`.
