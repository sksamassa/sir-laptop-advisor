import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "Подбор ноутбука методом SIR",
  description:
    "Сервис поддержки принятия решений: многокритериальный подбор ноутбука методом SIR с объяснением результата.",
};

const nav = [
  { href: "/", label: "Подбор" },
  { href: "/catalog", label: "Каталог" },
  { href: "/profile", label: "Профиль" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="font-sans antialiased">
        <div className="mx-auto flex min-h-screen w-full max-w-[1200px] flex-col px-4 pb-16 sm:px-6">
          <header className="sticky top-0 z-40 -mx-4 mb-8 px-4 py-4 backdrop-blur-xl sm:-mx-6 sm:px-6">
            <div className="card flex items-center justify-between gap-4 rounded-2xl px-4 py-3">
              <Link href="/" className="group flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-[#8b6bff] to-[#3ddc97] text-sm font-black text-[#06070f]">
                  SIR
                </span>
                <span className="leading-tight">
                  <span className="block text-xs font-semibold text-white sm:text-sm">
                    Подбор ноутбука
                  </span>
                  <span className="hidden text-[11px] text-[#8f96bd] sm:block">
                    многокритериальный выбор
                  </span>
                </span>
              </Link>
              <nav className="flex items-center gap-0.5 text-xs sm:gap-1 sm:text-sm">
                {nav.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="rounded-lg px-2 py-1.5 text-[#c3c8e6] transition hover:bg-white/5 hover:text-white sm:px-3 sm:py-2"
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>

          <main className="flex-1">{children}</main>

          <footer className="mt-14 flex flex-col gap-2 border-t border-white/5 pt-6 text-xs text-[#6f7699] sm:flex-row sm:items-center sm:justify-between">
            <span>
              Курсовая работа · метод SIR (Superiority and Inferiority Ranking)
            </span>
            <span>Цены в рублях · интерфейс на русском · объяснение каждого результата</span>
          </footer>
        </div>
      </body>
    </html>
  );
}
