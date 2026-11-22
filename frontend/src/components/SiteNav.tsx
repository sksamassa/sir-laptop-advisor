"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { me } from "@/lib/api";

const baseLinks = [
  { href: "/", label: "Подбор" },
  { href: "/catalog", label: "Каталог" },
];

export function SiteNav() {
  const pathname = usePathname();
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    me()
      .then(() => {
        if (!cancelled) setAuthenticated(true);
      })
      .catch(() => {
        if (!cancelled) setAuthenticated(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const links = [
    ...baseLinks,
    {
      href: "/profile",
      label: authenticated ? "Профиль" : "Войти",
    },
  ];

  return (
    <nav className="flex items-center gap-0.5 text-xs sm:gap-1 sm:text-sm" aria-label="Основная навигация">
      {links.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`relative rounded-lg px-2 py-1.5 transition sm:px-3 sm:py-2 ${
              active
                ? "bg-white/10 font-semibold text-white"
                : "text-[#c3c8e6] hover:bg-white/5 hover:text-white"
            }`}
          >
            {item.label}
            <span
              className={`absolute inset-x-2 -bottom-px h-px rounded-full bg-gradient-to-r from-[#8b6bff] to-[#3ddc97] transition-opacity sm:inset-x-3 ${
                active ? "opacity-100" : "opacity-0"
              }`}
              aria-hidden
            />
          </Link>
        );
      })}
    </nav>
  );
}
