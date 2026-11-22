"use client";

import type { Criterion } from "@/lib/api";

export function WeightEditor({
  criteria,
  weights,
  onChange,
}: {
  criteria: Criterion[];
  weights: Record<string, number>;
  onChange: (next: Record<string, number>) => void;
}) {
  const total = criteria.reduce((sum, criterion) => sum + (weights[criterion.key] ?? 0), 0);

  function setWeight(key: string, value: number) {
    onChange({ ...weights, [key]: Math.max(0, Math.min(100, Math.round(value))) });
  }

  function normalize() {
    const keys = criteria.map((criterion) => criterion.key);
    if (total === 0) {
      const even = Math.floor(100 / keys.length);
      const next: Record<string, number> = {};
      keys.forEach((key, index) => {
        next[key] = index === 0 ? 100 - even * (keys.length - 1) : even;
      });
      onChange(next);
      return;
    }
    const next: Record<string, number> = {};
    let assigned = 0;
    keys.forEach((key, index) => {
      if (index === keys.length - 1) {
        next[key] = 100 - assigned;
      } else {
        const scaled = Math.round(((weights[key] ?? 0) / total) * 100);
        next[key] = scaled;
        assigned += scaled;
      }
    });
    onChange(next);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs">
        <span className={total === 100 ? "text-[#3ddc97]" : "text-[#ffb3bf]"}>
          Сумма: {total}%{total === 100 ? " ✓" : ""}
        </span>
        <button type="button" className="text-[#a7adcd] underline-offset-2 hover:underline" onClick={normalize}>
          Выровнять до 100%
        </button>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className={`h-full rounded-full transition-all ${total === 100 ? "bg-[#3ddc97]" : "bg-[#ff6b81]"}`}
          style={{ width: `${Math.min(100, total)}%` }}
        />
      </div>
      {criteria.map((criterion) => (
        <div key={criterion.key}>
          <div className="flex items-center justify-between gap-3">
            <label className="text-sm text-[#c3c8e6]" htmlFor={`weight-${criterion.key}`}>
              {criterion.label_ru}
            </label>
            <span className="w-12 text-right text-sm font-semibold text-white">
              {weights[criterion.key] ?? 0}%
            </span>
          </div>
          <input
            id={`weight-${criterion.key}`}
            type="range"
            min={0}
            max={60}
            step={5}
            value={weights[criterion.key] ?? 0}
            onChange={(event) => setWeight(criterion.key, Number(event.target.value))}
            aria-label={`Важность критерия ${criterion.label_ru}`}
          />
        </div>
      ))}
    </div>
  );
}
