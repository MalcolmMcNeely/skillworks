import {
  createColumnHelper,
  createSortedRowModel,
  flexRender,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  sortFn_text,
  tableFeatures,
  useTable,
  type SortingState,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router';
import { activationsPath } from '../../activations/lib/activations';
import { describeDeliveries, describeTriggers } from '../../provenance/lib/provenance';
import type { SkillSummary } from '../api/skills';
import { ariaSort, describeList, describeMoney, describeSplit, sortMark } from '../lib/skills';
import { byActivations, type Sort } from '../lib/sorting';

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: {
    alphanumeric: sortFn_alphanumeric,
    basic: sortFn_basic,
    text: sortFn_text,
  },
});

const column = createColumnHelper<typeof features, SkillSummary>();

// Reads the address bar itself, because columns built once for the module cannot take props.
function ActivationsLink({ skill, count }: { skill: string; count: number }) {
  const [params] = useSearchParams();

  return count === 0 ? <>{count}</> : <Link to={activationsPath(params.toString(), skill)}>{count}</Link>;
}

// column.columns keeps each column's own value type, which a bare array widens away.
const columns = column.columns([
  column.accessor('name', { header: 'Skill' }),
  column.accessor('activations', {
    header: 'Activations',
    cell: (cell) => <ActivationsLink skill={cell.row.original.name} count={cell.getValue()} />,
  }),
  // Beside the count and before the money, so one row answers what fired, from where, and what it
  // cost, which is the whole reason the two stores are joined.
  column.accessor((skill) => describeTriggers(skill.origins), {
    id: 'trigger',
    header: 'Trigger',
  }),
  column.accessor((skill) => describeDeliveries(skill.origins), {
    id: 'delivery',
    header: 'Delivered by',
  }),
  // The money columns sort on the number and render the words, so clicking the heading ranks
  // skills by what they actually cost rather than by how the figure happens to read.
  column.accessor((skill) => skill.spend.cost, {
    id: 'cost',
    header: 'Cost',
    cell: (cell) => describeMoney(cell.getValue(), cell.row.original.spend.costIsPartial),
  }),
  column.accessor('averageCost', {
    header: 'Per activation',
    cell: (cell) => describeMoney(cell.getValue(), cell.row.original.spend.costIsPartial),
  }),
  column.accessor((skill) => describeSplit(skill.spend), {
    id: 'tokens',
    header: 'Tokens',
  }),
  column.accessor((skill) => describeList(skill.models), {
    id: 'models',
    header: 'Models',
  }),
  column.accessor((skill) => describeList(skill.repositories), {
    id: 'repositories',
    header: 'Repositories',
  }),
  column.accessor((skill) => describeList(skill.branches), {
    id: 'branches',
    header: 'Branches',
  }),
]);

const rowHeight = 34;

export function SkillTable({
  skills,
  sort,
  onSort,
}: {
  skills: SkillSummary[];
  sort: Sort;
  onSort: (sort: Sort) => void;
}) {
  // Keyed on the two values, not on the object: the sort is read fresh out of the address bar on
  // every render, so an object identity would miss every time and re-sort every row with it.
  const sorting: SortingState = useMemo(
    () => [{ id: sort.column, desc: sort.desc }],
    [sort.column, sort.desc],
  );

  const table = useTable({
    features,
    columns,
    data: skills,
    state: { sorting },
    onSortingChange: (change) => {
      const chosen = typeof change === 'function' ? change(sorting) : change;
      const [first] = chosen;

      // A third click clears the sort altogether, which would leave the table in whatever order the
      // API happened to answer in. Going back to the starting rank says something instead.
      onSort(first === undefined ? byActivations : { column: first.id, desc: first.desc });
    },
  });

  const rows = table.getRowModel().rows;
  const scroller = useRef<HTMLDivElement>(null);

  // Only the rows in view are in the DOM, so a catalogue of thousands scrolls like one of ten.
  // The virtualizer hands back methods rather than values, so React Compiler will not memoize this
  // component. Nothing downstream is memoized, so the cost is a skipped optimisation and no more.
  // oxlint-disable-next-line react/incompatible-library
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scroller.current,
    estimateSize: () => rowHeight,
    overscan: 12,
  });

  return (
    <div className="skills" role="table" aria-label="Skills">
      <div className="skills-head" role="rowgroup">
        {table.getHeaderGroups().map((group) => (
          <div className="skills-row" role="row" key={group.id}>
            {group.headers.map((header) => (
              <div
                className="skills-cell"
                role="columnheader"
                aria-sort={ariaSort(header.column.getIsSorted())}
                key={header.id}
              >
                <button type="button" onClick={header.column.getToggleSortingHandler()}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {sortMark(header.column.getIsSorted())}
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="skills-body" role="rowgroup" ref={scroller}>
        <div className="skills-runway" style={{ height: virtualizer.getTotalSize() }}>
          {virtualizer.getVirtualItems().map((item) => {
            const row = rows[item.index];

            return (
              <div
                className="skills-row"
                role="row"
                key={row.id}
                style={{ height: item.size, transform: `translateY(${item.start}px)` }}
              >
                {row.getAllCells().map((cell) => (
                  <div className="skills-cell" role="cell" key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
