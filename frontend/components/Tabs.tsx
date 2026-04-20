"use client";

import { useState, ReactNode } from "react";

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
  badge?: string | number;
}

export function Tabs({ tabs, initialId }: { tabs: Tab[]; initialId?: string }) {
  const [active, setActive] = useState(initialId || tabs[0]?.id);
  const current = tabs.find((t) => t.id === active) || tabs[0];

  return (
    <div>
      <div className="flex gap-1 overflow-x-auto border-b border-slate-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition border-b-2 -mb-px
              ${active === t.id
                ? "border-[#AF7225] text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"}`}
          >
            {t.label}
            {t.badge != null && (
              <span className="ml-2 text-xs bg-slate-200 rounded-full px-1.5 py-0.5 text-slate-600">
                {t.badge}
              </span>
            )}
          </button>
        ))}
      </div>
      <div>{current?.content}</div>
    </div>
  );
}
