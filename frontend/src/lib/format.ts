/** Russian formatting helpers. Money stays integer kopecks end to end. */

export function formatRub(minor: number): string {
  const rubles = Math.round(minor / 100);
  return `${rubles.toLocaleString("ru-RU")} \u20BD`;
}

export function formatScore(value: number): string {
  return value.toFixed(value >= 10 ? 1 : 3);
}

export function formatSigned(value: number): string {
  const rounded = value.toFixed(3);
  return value > 0 ? `+${rounded}` : rounded;
}

export function formatPercent(part: number, total: number): number {
  if (total <= 0) return 0;
  return Math.max(0, Math.min(100, (part / total) * 100));
}

export function formatCriterionValue(value: number, unit: string): string {
  switch (unit) {
    case "RUB":
      return formatRub(value);
    case "g":
      return `${Math.round(value)} г`;
    case "minutes":
      return `${Math.round(value)} мин`;
    case "GB":
      return `${Math.round(value)} ГБ`;
    case "months":
      return `${Math.round(value)} мес.`;
    case "score_0_10":
      return value.toFixed(1);
    case "points":
      return Math.round(value).toLocaleString("ru-RU");
    default:
      return String(value);
  }
}

export const osLabels: Record<string, string> = {
  windows: "Windows",
  macos: "macOS",
  linux: "Linux",
};

export const formLabels: Record<string, string> = {
  ultrabook: "Ультрабук",
  laptop: "Классический",
  gaming: "Игровой",
  convertible: "Трансформер",
};

export const goalLabels: Record<string, string> = {
  study: "Учёба",
  development: "Разработка",
  design: "Дизайн и видео",
  gaming: "Игры",
};
