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
import { useRef, useState } from 'react';
import type { SkillSummary } from '../api/skills';
import { ariaSort, describeList, sortMark } from '../lib/skills';

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

// column.columns keeps each column's own value type, which a bare array widens away.
const columns = column.columns([
  column.accessor('name', { header: 'Skill' }),
  column.accessor('activations', { header: 'Activations' }),
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

export function SkillTable({ skills }: { skills: SkillSummary[] }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'activations', desc: true }]);

  const table = useTable({
    features,
    columns,
    data: skills,
    state: { sorting },
    onSortingChange: setSorting,
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
