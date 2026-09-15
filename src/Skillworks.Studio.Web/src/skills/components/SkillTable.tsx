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
  // Beside the count and before the money, so one row answers what fired, from where, and what it cost.
  column.accessor((skill) => describeTriggers(skill.origins), {
    id: 'trigger',
    header: 'Trigger',
  }),
  column.accessor((skill) => describeDeliveries(skill.origins), {
    id: 'delivery',
    header: 'Delivered by',
  }),
  // Sorts on the number and renders the words, so the heading ranks skills by what they cost.
  column.accessor((skill) => skill.spend?.cost, {
    id: 'cost',
    header: 'Cost',
    // Undefined, not null: a cost not named is neither cheap nor dear, and only undefined sorts last both ways.
    sortUndefined: 'last',
    cell: (cell) => describeMoney(cell.getValue() ?? null),
  }),
  column.accessor((skill) => skill.averageCost ?? undefined, {
    id: 'averageCost',
    header: 'Per activation',
    sortUndefined: 'last',
    cell: (cell) => describeMoney(cell.getValue() ?? null),
  }),
  column.accessor((skill) => describeSplit(skill.spend), {
    id: 'tokens',
    header: 'Tokens',
  }),
  column.accessor((skill) => describeList(skill.models), {
    id: 'models',
    header: 'Models',
  }),
  column.accessor((skill) => describeList(skill.efforts), {
    id: 'efforts',
    header: 'Efforts',
  }),
  column.accessor((skill) => describeList(skill.repositories), {
    id: 'repositories',
    header: 'Repositories',
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
  // Keyed on the two values: the sort is a new object every render, so keying on it would re-sort every time.
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

      // A third click clears the sort, and the starting rank says more than the API's order.
      onSort(first === undefined ? byActivations : { column: first.id, desc: first.desc });
    },
  });

  const rows = table.getRowModel().rows;
  const scroller = useRef<HTMLDivElement>(null);

  // Virtualised for thousands of rows; React Compiler skips this component, and nothing downstream is memoized.
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
