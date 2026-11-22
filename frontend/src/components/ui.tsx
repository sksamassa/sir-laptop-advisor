"use client";

import type { ReactNode } from "react";

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`card p-5 sm:p-6 ${className}`}>{children}</section>;
}

export function SectionTitle({
  title,
  hint,
  right,
}: {
  title: string;
  hint?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {hint ? <p className="mt-0.5 text-xs text-[#8f96bd]">{hint}</p> : null}
      </div>
      {right}
    </div>
  );
}

export function ChipButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button type="button" className="chip" data-active={active} onClick={onClick} aria-pressed={active}>
      {children}
    </button>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-[#ff6b81]/40 bg-[#ff6b81]/10 px-3.5 py-2.5 text-sm text-[#ffb3bf]"
    >
      {children}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-xl ${className}`} aria-hidden />;
}

export function ScoreBar({ value, max }: { value: number; max: number }) {
  const width = max > 0 ? Math.max(2, Math.min(100, (Math.abs(value) / max) * 100)) : 2;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5" aria-hidden>
      <div
        className="h-full rounded-full bg-gradient-to-r from-[#8b6bff] to-[#3ddc97] transition-all"
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2.5">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[#8f96bd]">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${accent ? "text-[#3ddc97]" : "text-white"}`}>
        {value}
      </div>
    </div>
  );
}
