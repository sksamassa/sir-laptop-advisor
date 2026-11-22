"use client";

import { useEffect } from "react";

import type { ComparisonResponse } from "@/lib/api";
import { formatCriterionValue, formatRub } from "@/lib/format";

export function CompareDialog({
  comparison,
  onClose,
}: {
  comparison: ComparisonResponse;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-[#06070f]/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Сравнение моделей"
      onClick={onClose}
    >
      <div
        className="card max-h-[86vh] w-full max-w-4xl overflow-auto p-0 scroll-thin"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-white/5 bg-[#0a0c18]/95 px-5 py-4 backdrop-blur">
          <div>
            <h2 className="text-base font-semibold text-white">Сравнение моделей</h2>
            <p className="text-xs text-[#8f96bd]">Лучшее значение в каждой строке подсвечено</p>
          </div>
          <button type="button" className="btn btn-ghost px-3 py-1.5 text-xs" onClick={onClose}>
            Закрыть
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] border-collapse text-sm">
            <thead>
              <tr>
                <th className="sticky left-0 bg-[#0a0c18] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[#8f96bd]">
                  Критерий
                </th>
                {comparison.models.map((model) => (
                  <th key={model.id} className="px-4 py-3 text-left">
                    <div className="text-sm font-semibold text-white">{model.model_name}</div>
                    <div className="text-[11px] text-[#8f96bd]">
                      {formatRub(model.price_minor)} · место {model.rank}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparison.rows.map((row) => (
                <tr key={row.criterion} className="border-t border-white/5">
                  <th className="sticky left-0 bg-[#0a0c18] px-4 py-2.5 text-left text-xs font-medium text-[#c3c8e6]">
                    {row.label_ru}
                    <span className="ml-1 text-[10px] text-[#6f7699]">
                      {row.direction === "min" ? "↓" : "↑"}
                    </span>
                  </th>
                  {row.values.map((value, index) => (
                    <td
                      key={`${row.criterion}-${index}`}
                      className={`px-4 py-2.5 tabular-nums ${
                        index === row.best_index
                          ? "rounded-md bg-[#3ddc97]/10 font-semibold text-[#3ddc97]"
                          : "text-[#c3c8e6]"
                      }`}
                    >
                      {formatCriterionValue(value, row.unit)}
                    </td>
                  ))}
                </tr>
              ))}
              <tr className="border-t border-white/10">
                <th className="sticky left-0 bg-[#0a0c18] px-4 py-3 text-left text-xs font-medium text-[#c3c8e6]">
                  Итог SIR
                </th>
                {comparison.models.map((model, index) => (
                  <td
                    key={`score-${model.id}`}
                    className={`px-4 py-3 font-semibold tabular-nums ${
                      index === comparison.best_overall_index ? "text-[#3ddc97]" : "text-white"
                    }`}
                  >
                    {model.net_score.toFixed(3)}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
