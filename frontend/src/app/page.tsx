import { RankingWorkspace } from "@/features/ranking/RankingWorkspace";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="animate-rise">
        <div className="flex flex-wrap items-center gap-2 text-xs text-[#8f96bd]">
          <span className="chip">метод SIR</span>
          <span className="chip">7 критериев</span>
          <span className="chip">объяснение результата</span>
        </div>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl">
          <span className="gradient-text">Ноутбук, который подходит именно вам</span>
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[#a7adcd] sm:text-base">
          Укажите бюджет, задачи и важность характеристик. Сервис сравнит все доступные
          модели методом SIR и покажет не только лучший вариант, но и почему он лучший.
        </p>
      </section>

      <RankingWorkspace />
    </div>
  );
}
