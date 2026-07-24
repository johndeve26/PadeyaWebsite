"use client";

import { Modal } from "@/components/ui";
import {
  parseSizeChartJson,
  type MerchSizeChartPublic,
} from "@/lib/merch-size-chart";

type Props = {
  open: boolean;
  onClose: () => void;
  chart: MerchSizeChartPublic | null | undefined;
};

export function MerchSizeGuideModal({ open, onClose, chart }: Props) {
  if (!chart) return null;

  const table = parseSizeChartJson(chart.chart_json);
  const unitsLabel = chart.units === "inches" ? "inches" : "cm";

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Size guide"
      description={`${chart.name} · measurements in ${unitsLabel}`}
      className="sm:max-w-2xl"
    >
      <div className="space-y-4">
        {chart.fit_notes ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {chart.fit_notes}
          </p>
        ) : null}

        {table ? (
          <div className="-mx-1 overflow-x-auto">
            <table className="w-full min-w-[280px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                  {table.columns.map((col) => (
                    <th
                      key={col}
                      scope="col"
                      className="px-2 py-2 font-extrabold text-foreground first:pl-0 last:pr-0"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, idx) => (
                  <tr
                    key={`${row[0] ?? "row"}-${idx}`}
                    className="border-b border-border/70 last:border-0"
                  >
                    {table.columns.map((_, colIdx) => (
                      <td
                        key={`${idx}-${colIdx}`}
                        className="px-2 py-2.5 text-muted-foreground first:pl-0 first:font-semibold first:text-foreground last:pr-0"
                      >
                        {row[colIdx] ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Size chart data is unavailable for this product.
          </p>
        )}
      </div>
    </Modal>
  );
}
