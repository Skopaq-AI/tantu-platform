"use client";
import { useState, useEffect } from "react";
import { I18nContext, Lang } from "@/lib/i18n";

export function I18nProvider({ children, defaultLang = "en" }: { children: React.ReactNode; defaultLang?: Lang }) {
  const [lang, setLangState] = useState<Lang>(defaultLang as Lang);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? (localStorage.getItem("tantu_lang") as Lang | null) : null;
    if (saved && ["en", "hi", "ta", "te", "kn"].includes(saved)) setLangState(saved);
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    if (typeof window !== "undefined") localStorage.setItem("tantu_lang", l);
  };

  return <I18nContext.Provider value={{ lang, setLang }}>{children}</I18nContext.Provider>;
}
