"use client";

import { useEffect, useState } from "react";

import {
  ApiError,
  getCriteria,
  getProfile,
  login,
  logout,
  me,
  register,
  saveProfile,
} from "@/lib/api";
import type { Criterion, Profile, SessionUser } from "@/lib/api";
import { ChipButton, ErrorNote, Panel, SectionTitle, Skeleton } from "@/components/ui";
import { goalLabels, formatRub } from "@/lib/format";
import { WeightEditor } from "@/features/ranking/WeightEditor";

const FALLBACK_WEIGHTS: Record<string, number> = {
  price: 20,
  performance: 20,
  memory: 15,
  weight: 10,
  battery: 20,
  screen: 10,
  warranty: 5,
};

export default function ProfilePage() {
  const [user, setUser] = useState<SessionUser | null | undefined>(undefined);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [goals, setGoals] = useState<string[]>(["study"]);
  const [budgetRub, setBudgetRub] = useState(90_000);
  const [weights, setWeights] = useState<Record<string, number>>(FALLBACK_WEIGHTS);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);

  useEffect(() => {
    me()
      .then((payload) => setUser(payload.user))
      .catch(() => setUser(null));
    getCriteria()
      .then((payload) => setCriteria(payload.criteria))
      .catch(() => setCriteria([]));
  }, []);

  useEffect(() => {
    if (!user) return;
    getProfile()
      .then((payload) => {
        setProfile(payload);
        setGoals(payload.goals);
        setBudgetRub(Math.round(payload.budget_minor / 100));
        const percentages: Record<string, number> = {};
        for (const [key, value] of Object.entries(payload.weights)) {
          percentages[key] = Math.round(value * 100);
        }
        setWeights(percentages);
      })
      .catch(() => setProfile(null));
  }, [user]);

  async function submitAuth() {
    setAuthBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === "register") {
        await register(email, password);
      }
      const session = await login(email, password);
      setUser(session.user);
      setPassword("");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Не удалось войти");
    } finally {
      setAuthBusy(false);
    }
  }

  async function signOut() {
    await logout().catch(() => undefined);
    setUser(null);
    setProfile(null);
  }

  async function submitProfile() {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await saveProfile(
        {
          goals,
          budget_minor: budgetRub * 100,
          preferred_brand: null,
          preferred_os: null,
          form_factor: null,
          weights: Object.fromEntries(
            Object.entries(weights).map(([key, value]) => [key, value / 100]),
          ),
        },
        false,
      );
      setProfile(saved);
      setNotice(`Сохранено (ревизия ${saved.revision})`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Не удалось сохранить профиль");
    } finally {
      setSaving(false);
    }
  }

  if (user === undefined) {
    return (
      <div className="mx-auto max-w-xl space-y-3">
        <Skeleton className="h-10" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-md">
        <h1 className="text-3xl font-semibold tracking-tight">
          <span className="gradient-text">Аккаунт</span>
        </h1>
        <p className="mb-6 mt-2 text-sm text-[#a7adcd]">
          Сохраните веса критериев и бюджет, чтобы не вводить их заново.
        </p>
        <Panel>
          <div className="mb-5 flex gap-2">
            <button
              type="button"
              className="chip"
              data-active={mode === "login"}
              onClick={() => setMode("login")}
            >
              Вход
            </button>
            <button
              type="button"
              className="chip"
              data-active={mode === "register"}
              onClick={() => setMode("register")}
            >
              Регистрация
            </button>
          </div>
          <div className="space-y-4">
            <div>
              <label className="label" htmlFor="email">
                Электронная почта
              </label>
              <input
                id="email"
                className="field"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="password">
                Пароль
              </label>
              <input
                id="password"
                className="field"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              {mode === "register" ? (
                <p className="mt-1 text-xs text-[#8f96bd]">Не менее 12 символов</p>
              ) : null}
            </div>
            {error ? <ErrorNote>{error}</ErrorNote> : null}
            <button
              type="button"
              className="btn btn-primary w-full"
              disabled={authBusy || email.length < 3 || password.length < 1}
              onClick={submitAuth}
            >
              {authBusy ? "Подождите…" : mode === "login" ? "Войти" : "Создать аккаунт"}
            </button>
          </div>
        </Panel>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">
            <span className="gradient-text">Профиль</span>
          </h1>
          <p className="mt-1 text-sm text-[#a7adcd]">
            {user.email}
            {profile ? ` · ревизия ${profile.revision}` : " · профиль ещё не сохранён"}
          </p>
        </div>
        <button type="button" className="btn btn-ghost" onClick={signOut}>
          Выйти
        </button>
      </div>

      <Panel>
        <SectionTitle title="Предпочтения" hint="Эти значения будут доступны при подборе" />

        <div className="space-y-5">
          <div>
            <span className="label">Цели использования</span>
            <div className="flex flex-wrap gap-2">
              {Object.entries(goalLabels).map(([goal, label]) => (
                <ChipButton
                  key={goal}
                  active={goals.includes(goal)}
                  onClick={() =>
                    setGoals((current) =>
                      current.includes(goal)
                        ? current.filter((item) => item !== goal)
                        : [...current, goal],
                    )
                  }
                >
                  {label}
                </ChipButton>
              ))}
            </div>
          </div>

          <div>
            <label className="label" htmlFor="profile-budget">
              Бюджет — {formatRub(budgetRub * 100)}
            </label>
            <input
              id="profile-budget"
              type="range"
              min={30_000}
              max={300_000}
              step={1_000}
              value={budgetRub}
              onChange={(event) => setBudgetRub(Number(event.target.value))}
            />
          </div>

          <div>
            <span className="label">Веса критериев</span>
            {criteria.length > 0 ? (
              <WeightEditor criteria={criteria} weights={weights} onChange={setWeights} />
            ) : null}
          </div>

          {error ? <ErrorNote>{error}</ErrorNote> : null}
          {notice ? (
            <div className="rounded-xl border border-[#3ddc97]/30 bg-[#3ddc97]/10 px-3.5 py-2.5 text-sm text-[#9ff0c8]">
              {notice}
            </div>
          ) : null}

          <button
            type="button"
            className="btn btn-primary w-full"
            disabled={saving || goals.length === 0}
            onClick={submitProfile}
          >
            {saving ? "Сохраняем…" : "Сохранить профиль"}
          </button>
        </div>
      </Panel>
    </div>
  );
}
