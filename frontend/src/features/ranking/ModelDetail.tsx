"use client";

import type { Criterion, RankingItem } from "@/lib/api";
import { formatSigned } from "@/lib/format";

function labelFor(criteria: Criterion[], key: string): string {
  const label = criteria.find((criterion) => criterion.key === key)?.label_ru ?? key;
  return label.charAt(0).toLowerCase() + label.slice(1);
}

export function ModelDetail({
  item,
  criteria,
}: {
  item: RankingItem;
  criteria: Criterion[];
}) {
  const maxContribution = Math.max(
    0.0001,
    ...Object.values(item.contributions).map((entry) => Math.abs(entry.contribution)),
  );

  return (
    <div className="mt-4 grid gap-2 rounded-xl border border-white/5 bg-[#06070f]/50 p-4">
      <div className="mb-1 grid grid-cols-[1fr_auto] items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-[#8f96bd]">
        <span>Критерий</span>
        <span>Вклад в оценку</span>
      </div>
      {criteria.map((criterion) => {
        const entry = item.contributions[criterion.key];
        if (!entry) return null;
        const positive = entry.contribution >= 0;
        const width = Math.min(100, (Math.abs(entry.contribution) / maxContribution) * 50);
        return (
          <div key={criterion.key} className="grid grid-cols-[1fr_auto] items-center gap-3">
            <div className="min-w-0">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-xs text-[#c3c8e6]">{criterion.label_ru}</span>
                <span className="text-[10px] text-[#6f7699]">
                  {(entry.normalized * 100).toFixed(0)}%
                </span>
              </div>
              <div className="relative mt-1 h-1.5 rounded-full bg-white/5">
                <div className="absolute left-1/2 top-0 h-full w-px bg-white/10" />
                <div
                  className={`absolute top-0 h-full rounded-full ${
                    positive ? "bg-[#3ddc97]" : "bg-[#ff6b81]"
                  }`}
                  style={
                    positive
                      ? { left: "50%", width: `${width}%` }
                      : { right: "50%", width: `${width}%` }
                  }
                />
              </div>
            </div>
            <span
              className={`w-16 text-right text-xs font-semibold tabular-nums ${
                positive ? "text-[#3ddc97]" : "text-[#ff8fa0]"
              }`}
            >
              {formatSigned(entry.contribution)}
            </span>
          </div>
        );
      })}
      <div className="mt-2 grid grid-cols-3 gap-2 border-t border-white/5 pt-3 text-center">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[#8f96bd]">Φ+</div>
          <div className="text-sm text-white">{item.phi_plus.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[#8f96bd]">Φ−</div>
          <div className="text-sm text-white">{item.phi_minus.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[#8f96bd]">SIR</div>
          <div className="text-sm font-semibold text-[#3ddc97]">{item.net_score.toFixed(3)}</div>
        </div>
      </div>

      {item.gap_to_top ? (
        <div className="mt-3 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-[#8f96bd]">
            До лидера
          </div>
          <div className="mt-1 flex flex-wrap items-baseline gap-2">
            <span className="text-sm font-semibold tabular-nums text-[#ffb3bf]">
              {item.gap_to_top.gap.toFixed(3)}
            </span>
            <span className="text-xs text-[#a7adcd]">
              {item.gap_to_top.decisive_criteria.length === 0
                ? "лидер не опережает ни по одному критерию"
                : item.gap_to_top.decisive_criteria
                    .map(
                      (entry) =>
                        `${labelFor(criteria, entry.criterion)} ${entry.delta.toFixed(2)}`,
                    )
                    .join(" · ")}
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
