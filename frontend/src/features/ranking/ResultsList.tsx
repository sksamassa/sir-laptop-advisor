"use client";

import { useState } from "react";

import type { Criterion, RankingResponse } from "@/lib/api";
import { formatRub } from "@/lib/format";
import { ScoreBar } from "@/components/ui";

import { ModelDetail } from "./ModelDetail";

export function ResultsList({
  result,
  criteria,
  selected,
  onToggle,
}: {
  result: RankingResponse;
  criteria: Criterion[];
  selected: string[];
  onToggle: (modelId: string) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (result.items.length === 0) {
    const cheapest = result.cheapest_price_minor;
    return (
      <div className="card p-8 text-center">
        <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-white/5 text-xl">
          🔍
        </div>
        <h3 className="text-base font-semibold text-white">Подходящих моделей нет</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-[#8f96bd]">
          {result.empty_reason === "budget_too_low" ? (
            <>
              {cheapest
                ? `В каталоге нет моделей до этой суммы. Самая доступная — ${formatRub(cheapest)}.`
                : "В каталоге пока нет моделей в этом бюджете."}{" "}
              Увеличьте бюджет или ослабьте фильтры — и мы пересчитаем рейтинг.
            </>
          ) : (
            "Попробуйте изменить бюджет или критерии."
          )}
        </p>
      </div>
    );
  }

  const maxAbs = Math.max(...result.items.map((item) => Math.abs(item.net_score)), 0.0001);

  return (
    <ol className="space-y-3">
      {result.items.map((item, index) => {
        const isSelected = selected.includes(item.model.id);
        const isOpen = expanded === item.model.id;
        const top = item.rank <= 3;
        return (
          <li
            key={item.model.id}
            className={`card animate-rise p-4 transition sm:p-5 ${
              isSelected ? "ring-1 ring-[#7c5cff]/70" : ""
            }`}
            style={{ animationDelay: `${Math.min(index * 40, 240)}ms` }}
          >
            <div className="flex items-start gap-3 sm:gap-4">
              <div
                className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl text-sm font-black ${
                  top
                    ? "bg-gradient-to-br from-[#8b6bff] to-[#3ddc97] text-[#06070f]"
                    : "border border-white/10 bg-white/5 text-[#c3c8e6]"
                }`}
                aria-label={`Место ${item.rank}`}
              >
                {item.rank}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <h3 className="truncate text-base font-semibold text-white">
                    {item.model.model_name}
                  </h3>
                  <span className="text-xs text-[#8f96bd]">{item.model.brand}</span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#a7adcd]">
                  <span className="font-semibold text-white">{formatRub(item.model.price_minor)}</span>
                  <span>{item.model.values.memory} ГБ RAM</span>
                  <span>{item.model.values.battery} мин</span>
                  <span>{(item.model.values.weight / 1000).toFixed(2)} кг</span>
                </div>

                <div className="mt-3 flex items-center gap-3">
                  <div className="flex-1">
                    <ScoreBar value={item.net_score} max={maxAbs} />
                  </div>
                  <span className="w-20 text-right text-sm font-semibold tabular-nums text-[#3ddc97]">
                    {item.net_score.toFixed(3)}
                  </span>
                </div>

                <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-[#8f96bd]">
                  {item.reason}
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="btn btn-ghost px-3 py-1.5 text-xs"
                    aria-expanded={isOpen}
                    onClick={() => setExpanded(isOpen ? null : item.model.id)}
                  >
                    {isOpen ? "Свернуть" : "Почему так?"}
                  </button>
                  <button
                    type="button"
                    className="chip"
                    data-active={isSelected}
                    aria-pressed={isSelected}
                    onClick={() => onToggle(item.model.id)}
                    disabled={!isSelected && selected.length >= 4}
                  >
                    {isSelected ? "✓ В сравнении" : "Сравнить"}
                  </button>
                  {selected.length >= 4 && !isSelected ? (
                    <span className="text-[10px] text-[#6f7699]">не более 4 моделей</span>
                  ) : null}
                </div>

                {isOpen ? <ModelDetail item={item} criteria={criteria} /> : null}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
