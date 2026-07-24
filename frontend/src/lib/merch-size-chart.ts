/** Shared shape for reusable Pàdéyá merch size charts (`chart_json`). */

export type MerchSizeChartJson = {
  columns: string[];
  rows: Array<Array<string | number>>;
};

export type MerchSizeChartPublic = {
  id: string;
  name: string;
  product_type?: string | null;
  units: string;
  chart_json: unknown;
  fit_notes?: string | null;
  status?: string;
};

export type MerchSizeChart = MerchSizeChartPublic & {
  host_id: string;
  created_at?: string;
  updated_at?: string;
  archived_at?: string | null;
};

export const TEE_CHART_EXAMPLE: MerchSizeChartJson = {
  columns: ["Size", "Chest", "Length", "Sleeve"],
  rows: [
    ["S", "96", "68", "20"],
    ["M", "102", "70", "21"],
    ["L", "108", "72", "22"],
    ["XL", "114", "74", "23"],
  ],
};

export const CAP_CHART_EXAMPLE: MerchSizeChartJson = {
  columns: ["Size", "Circumference"],
  rows: [["One size", "58"]],
};

export function parseSizeChartJson(value: unknown): MerchSizeChartJson | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as { columns?: unknown; rows?: unknown };
  if (!Array.isArray(raw.columns) || !Array.isArray(raw.rows)) return null;
  const columns = raw.columns.map((c) => String(c));
  if (columns.length === 0) return null;
  const rows = raw.rows
    .filter((row): row is unknown[] => Array.isArray(row))
    .map((row) => row.map((cell) => (cell == null ? "" : String(cell))));
  return { columns, rows };
}
