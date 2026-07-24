/** Quick date-range presets for analytics dashboards. */

export type AnalyticsRangeKey = "7d" | "30d" | "90d" | "365d";

export const ANALYTICS_RANGE_OPTIONS: {
  key: AnalyticsRangeKey;
  label: string;
  days: number;
}[] = [
  { key: "7d", label: "7 days", days: 7 },
  { key: "30d", label: "30 days", days: 30 },
  { key: "90d", label: "90 days", days: 90 },
  { key: "365d", label: "12 months", days: 365 },
];

export function rangeToQuery(key: AnalyticsRangeKey): {
  date_from: string;
  date_to: string;
} {
  const opt = ANALYTICS_RANGE_OPTIONS.find((o) => o.key === key) ?? ANALYTICS_RANGE_OPTIONS[2];
  const date_to = new Date();
  const date_from = new Date(date_to.getTime() - opt.days * 24 * 60 * 60 * 1000);
  return {
    date_from: date_from.toISOString(),
    date_to: date_to.toISOString(),
  };
}
