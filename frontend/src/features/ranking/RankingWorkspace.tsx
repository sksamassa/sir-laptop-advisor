"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  compareRanking,
  createRanking,
  getCriteria,
  me,
} from "@/lib/api";
import type { ComparisonResponse, Criterion, RankingResponse } from "@/lib/api";
import { ChipButton, ErrorNote, Panel, SectionTitle, Skeleton } from "@/components/ui";
import { formatRub, goalLabels, osLabels, formLabels } from "@/lib/format";

import { CompareDialog } from "./CompareDialog";
import { ResultsList } from "./ResultsList";
import { WeightEditor } from "./WeightEditor";

const DEFAULT_WEIGHTS: Record<string, number> = {
  price: 20,
  performance: 20,
  memory: 15,
  weight: 10,
  battery: 20,
  screen: 10,
  warranty: 5,
};

export function RankingWorkspace() {
  const [criteria, setCriteria] = useState<Criterion[] | null>(null);
  const [vocabularies, setVocabularies] = useState<{
    goals: string[];
    os: string[];
    form_factor: string[];
  } | null>(null);
  const [criteriaError, setCriteriaError] = useState<string | null>(null);

  const [budgetRub, setBudgetRub] = useState(90_000);
  const [goals, setGoals] = useState<string[]>(["study", "development"]);
  const [weights, setWeights] = useState<Record<string, number>>(DEFAULT_WEIGHTS);
  const [brand, setBrand] = useState("");
  const [os, setOs] = useState<string | null>(null);
  const [form, setForm] = useState<string | null>(null);

  const [result, setResult] = useState<RankingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [useSavedWeights, setUseSavedWeights] = useState(false);

  useEffect(() => {
    me()
      .then(() => setAuthenticated(true))
      .catch(() => setAuthenticated(false));
  }, []);

  useEffect(() => {
    let cancelled = false;
    getCriteria()
      .then((payload) => {
        if (cancelled) return;
        setCriteria(payload.criteria);
        setVocabularies(payload.vocabularies);
        const keys = payload.criteria.map((criterion) => criterion.key);
        setWeights((current) => {
          const next: Record<string, number> = {};
          for (const key of keys) next[key] = current[key] ?? 0;
          return next;
        });
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setCriteriaError(
            cause instanceof ApiError ? cause.message : "Не удалось загрузить критерии",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const weightTotal = useMemo(
    () => Object.values(weights).reduce((sum, value) => sum + value, 0),
    [weights],
  );
  const criteriaReady = (criteria?.length ?? 0) > 0;
  const weightsValid = weightTotal === 100 && criteriaReady;

  const toggleGoal = (goal: string) => {
    setGoals((current) =>
      current.includes(goal) ? current.filter((item) => item !== goal) : [...current, goal],
    );
  };

  const toggleSelected = (modelId: string) => {
    setSelected((current) => {
      if (current.includes(modelId)) return current.filter((id) => id !== modelId);
      if (current.length >= 4) return current;
      return [...current, modelId];
    });
  };

  async function submit() {
    if (!weightsValid || goals.length === 0) return;
    setLoading(true);
    setError(null);
    setSelected([]);
    try {
      const usingSaved = authenticated && useSavedWeights;
      const payload = await createRanking({
        budget_minor: Math.round(budgetRub * 100),
        goals,
        ...(usingSaved
          ? { use_saved_weights: true }
          : {
              weights: Object.fromEntries(
                Object.entries(weights).map(([key, value]) => [key, value / 100]),
              ),
            }),
        preferred_brand: brand.trim() ? brand.trim() : null,
        preferred_os: os,
        form_factor: form,
      });
      setResult(payload);
    } catch (cause) {
      setResult(null);
      setError(cause instanceof ApiError ? cause.message : "Не удалось получить рекомендации");
    } finally {
      setLoading(false);
    }
  }

  async function openComparison() {
    if (!result || selected.length < 2) return;
    setCompareLoading(true);
    setCompareError(null);
    try {
      setComparison(await compareRanking(result.ranking_id, selected));
    } catch (cause) {
      setCompareError(cause instanceof ApiError ? cause.message : "Не удалось сравнить модели");
    } finally {
      setCompareLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
      <Panel className="h-fit lg:sticky lg:top-24">
        <SectionTitle title="Ваши предпочтения" hint="Пять параметров — и список готов" />

        <div className="space-y-5">
          <div>
            <label className="label" htmlFor="budget">
              Бюджет
            </label>
            <div className="flex items-center gap-3">
              <input
                id="budget"
                type="range"
                min={30_000}
                max={300_000}
                step={1_000}
                value={budgetRub}
                onChange={(event) => setBudgetRub(Number(event.target.value))}
                aria-label="Бюджет"
              />
              <div className="w-32 shrink-0">
                <input
                  className="field text-right"
                  inputMode="numeric"
                  value={budgetRub}
                  onChange={(event) => {
                    const value = Number(event.target.value.replace(/\D/g, ""));
                    setBudgetRub(Number.isFinite(value) ? Math.min(1_000_000, value) : 0);
                  }}
                  aria-label="Бюджет в рублях"
                />
              </div>
            </div>
            <p className="mt-1 text-xs text-[#8f96bd]">до {formatRub(budgetRub * 100)}</p>
          </div>

          <div>
            <span className="label">Для чего ноутбук</span>
            <div className="flex flex-wrap gap-2">
              {(vocabularies?.goals ?? Object.keys(goalLabels)).map((goal) => (
                <ChipButton key={goal} active={goals.includes(goal)} onClick={() => toggleGoal(goal)}>
                  {goalLabels[goal] ?? goal}
                </ChipButton>
              ))}
            </div>
          </div>

          <div>
            <span className="label">Важность критериев</span>
            {criteria ? (
              <WeightEditor criteria={criteria} weights={weights} onChange={setWeights} />
            ) : (
              <div className="space-y-2">
                {Array.from({ length: 7 }).map((_, index) => (
                  <Skeleton key={index} className="h-9" />
                ))}
              </div>
            )}
          </div>

          <details className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
            <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-[#8f96bd]">
              Мягкие предпочтения
            </summary>
            <div className="mt-3 space-y-3">
              <div>
                <label className="label" htmlFor="brand">
                  Бренд
                </label>
                <input
                  id="brand"
                  className="field"
                  placeholder="Например, Lenovo"
                  value={brand}
                  maxLength={60}
                  onChange={(event) => setBrand(event.target.value)}
                />
              </div>
              <div>
                <span className="label">Операционная система</span>
                <div className="flex flex-wrap gap-2">
                  {(vocabularies?.os ?? ["windows", "macos", "linux"]).map((value) => (
                    <ChipButton
                      key={value}
                      active={os === value}
                      onClick={() => setOs((current) => (current === value ? null : value))}
                    >
                      {osLabels[value] ?? value}
                    </ChipButton>
                  ))}
                </div>
              </div>
              <div>
                <span className="label">Форм-фактор</span>
                <div className="flex flex-wrap gap-2">
                  {(vocabularies?.form_factor ?? ["ultrabook", "laptop", "gaming", "convertible"]).map(
                    (value) => (
                      <ChipButton
                        key={value}
                        active={form === value}
                        onClick={() => setForm((current) => (current === value ? null : value))}
                      >
                        {formLabels[value] ?? value}
                      </ChipButton>
                    ),
                  )}
                </div>
              </div>
            </div>
          </details>

          {authenticated ? (
            <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5 text-xs text-[#c3c8e6]">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[#7c5cff]"
                checked={useSavedWeights}
                onChange={(event) => setUseSavedWeights(event.target.checked)}
              />
              Использовать веса из профиля
            </label>
          ) : null}

          {criteriaError ? <ErrorNote>{criteriaError}</ErrorNote> : null}
          {error ? <ErrorNote>{error}</ErrorNote> : null}

          <button
            type="button"
            className="btn btn-primary w-full"
            disabled={!weightsValid || goals.length === 0 || loading}
            onClick={submit}
          >
            {loading ? "Считаем рейтинг…" : "Подобрать ноутбук"}
          </button>
          {criteriaReady && weightTotal !== 100 ? (
            <p className="text-center text-xs text-[#8f96bd]">
              Сумма весов: {weightTotal}% — выровняйте до 100%, чтобы продолжить
            </p>
          ) : null}
        </div>
      </Panel>

      <div className="space-y-4">
        {result ? (
          <div className="card flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div>
              <div className="text-sm text-white">
                Найдено моделей: <span className="font-semibold">{result.candidate_count}</span>
              </div>
              <div className="text-[11px] text-[#8f96bd]">
                алгоритм {result.algorithm_version} · критерии {result.criteria_version.slice(0, 12)}…
              </div>
            </div>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={selected.length < 2 || compareLoading}
              onClick={openComparison}
            >
              {compareLoading ? "Сравниваем…" : `Сравнить ${selected.length || ""}`.trim()}
            </button>
          </div>
        ) : null}

        {compareError ? <ErrorNote>{compareError}</ErrorNote> : null}

        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </div>
        ) : result ? (
          <ResultsList
            result={result}
            criteria={criteria ?? []}
            selected={selected}
            onToggle={toggleSelected}
          />
        ) : (
          <Panel className="border-dashed">
            <div className="py-10 text-center">
              <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-white/5 text-xl">
                🎯
              </div>
              <h3 className="text-base font-semibold text-white">Рейтинг появится здесь</h3>
              <p className="mx-auto mt-2 max-w-sm text-sm text-[#8f96bd]">
                Заполните бюджет, задачи и веса критериев слева. Мы покажем упорядоченный
                список с оценкой SIR и объяснением для каждой модели.
              </p>
            </div>
          </Panel>
        )}
      </div>

      {comparison ? (
        <CompareDialog comparison={comparison} onClose={() => setComparison(null)} />
      ) : null}
    </div>
  );
}
