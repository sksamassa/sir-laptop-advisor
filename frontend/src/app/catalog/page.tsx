"use client";

import { useEffect, useState } from "react";

import { ApiError, getCatalog } from "@/lib/api";
import type { CatalogPage } from "@/lib/api";
import { ChipButton, ErrorNote, Panel, SectionTitle, Skeleton } from "@/components/ui";
import { formLabels, formatRub, osLabels } from "@/lib/format";

const PAGE_SIZE = 12;

export default function CatalogPage() {
  const [query, setQuery] = useState("");
  const [os, setOs] = useState<string | null>(null);
  const [form, setForm] = useState<string | null>(null);
  const [maxPrice, setMaxPrice] = useState(250_000);
  const [page, setPage] = useState(1);

  const [data, setData] = useState<CatalogPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(() => {
      getCatalog({
        query: query.trim() || undefined,
        os: os ?? undefined,
        formFactor: form ?? undefined,
        maxPriceMinor: maxPrice * 100,
        page,
        pageSize: PAGE_SIZE,
      })
        .then((payload) => {
          if (!cancelled) {
            setData(payload);
            setError(null);
          }
        })
        .catch((cause: unknown) => {
          if (!cancelled) {
            setError(cause instanceof ApiError ? cause.message : "Не удалось загрузить каталог");
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, os, form, maxPrice, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          <span className="gradient-text">Каталог моделей</span>
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[#a7adcd]">
          Все активные модели с семью критериями. Фильтры сужают каталог, порядок остаётся по цене.
        </p>
      </div>

      <Panel>
        <SectionTitle title="Фильтры" hint={`Найдено: ${data?.total ?? 0}`} />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <label className="label" htmlFor="q">
              Поиск по названию
            </label>
            <input
              id="q"
              className="field"
              placeholder="Например, ZenBook"
              value={query}
              onChange={(event) => {
                setPage(1);
                setQuery(event.target.value);
              }}
            />
          </div>
          <div>
            <span className="label">ОС</span>
            <div className="flex flex-wrap gap-2">
              {["windows", "macos", "linux"].map((value) => (
                <ChipButton
                  key={value}
                  active={os === value}
                  onClick={() => {
                    setPage(1);
                    setOs((current) => (current === value ? null : value));
                  }}
                >
                  {osLabels[value]}
                </ChipButton>
              ))}
            </div>
          </div>
          <div>
            <span className="label">Форм-фактор</span>
            <div className="flex flex-wrap gap-2">
              {["ultrabook", "laptop", "gaming", "convertible"].map((value) => (
                <ChipButton
                  key={value}
                  active={form === value}
                  onClick={() => {
                    setPage(1);
                    setForm((current) => (current === value ? null : value));
                  }}
                >
                  {formLabels[value]}
                </ChipButton>
              ))}
            </div>
          </div>
          <div className="md:col-span-2 lg:col-span-4">
            <label className="label" htmlFor="max-price">
              Максимальная цена — {formatRub(maxPrice * 100)}
            </label>
            <input
              id="max-price"
              type="range"
              min={30_000}
              max={300_000}
              step={5_000}
              value={maxPrice}
              onChange={(event) => {
                setPage(1);
                setMaxPrice(Number(event.target.value));
              }}
            />
          </div>
        </div>
      </Panel>

      {error ? <ErrorNote>{error}</ErrorNote> : null}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((model) => (
              <article key={model.id} className="card flex h-full flex-col p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="text-sm font-semibold text-white">{model.model_name}</h2>
                    <p className="text-xs text-[#8f96bd]">{model.brand}</p>
                  </div>
                  <span className="chip">{osLabels[model.os] ?? model.os}</span>
                </div>
                <div className="mt-3 text-lg font-semibold text-white">
                  {formatRub(model.price_minor)}
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs text-[#a7adcd]">
                  <div className="flex justify-between">
                    <dt className="text-[#6f7699]">CPU</dt>
                    <dd>{model.values.performance.toLocaleString("ru-RU")}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-[#6f7699]">RAM</dt>
                    <dd>{model.values.memory} ГБ</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-[#6f7699]">Вес</dt>
                    <dd>{(model.values.weight / 1000).toFixed(2)} кг</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-[#6f7699]">Батарея</dt>
                    <dd>{Math.round(model.values.battery / 60)} ч</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-[#6f7699]">Экран</dt>
                    <dd>{model.values.screen.toFixed(1)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-[#6f7699]">Гарантия</dt>
                    <dd>{model.values.warranty} мес.</dd>
                  </div>
                </dl>
                <div className="mt-auto pt-3">
                  <span className="chip">{formLabels[model.form_factor] ?? model.form_factor}</span>
                </div>
              </article>
            ))}
          </div>

          <div className="flex items-center justify-center gap-3">
            <button
              type="button"
              className="btn btn-ghost"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Назад
            </button>
            <span className="text-xs text-[#8f96bd]">
              Страница {page} из {totalPages}
            </span>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
            >
              Вперёд
            </button>
          </div>
        </>
      ) : (
        <div className="card p-10 text-center">
          <h2 className="text-base font-semibold text-white">Ничего не найдено</h2>
          <p className="mt-2 text-sm text-[#8f96bd]">
            Ослабьте фильтры: увеличьте цену или снимите ограничения по ОС и форм-фактору.
          </p>
        </div>
      )}
    </div>
  );
}
