"use client";
import { useRouter, usePathname } from "next/navigation";

interface BottomNavProps {
  userId: string;
}

export function BottomNavApp({ userId }: BottomNavProps) {
  const router = useRouter();
  const pathname = usePathname();

  const tabs = [
    { icon: "🔥", label: "Анкеты", path: "/app", exact: true },
    { icon: "💌", label: "Матчи", path: "/app/matches", exact: false },
    { icon: "🧠", label: "AI Чат", path: "/app/ai-advisor", highlight: true, exact: false },
    { icon: "👤", label: "Профиль", path: "/app/profile", exact: false },
    { icon: "⭐", label: "Premium", path: "/app/premium", exact: false },
  ];

  const navigate = (path: string) => router.push(path);

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 bg-content1 border-t border-divider z-50"
      style={{ paddingBottom: "env(safe-area-inset-bottom)", touchAction: "manipulation" }}
    >
      <div className="max-w-lg mx-auto flex">
        {tabs.map((tab) => {
          const isActive = tab.exact ? pathname === tab.path : pathname?.startsWith(tab.path);
          return (
            <button
              key={tab.path}
              onClick={() => navigate(tab.path)}
              className={`flex-1 flex flex-col items-center py-2 gap-0.5 transition-colors ${
                isActive ? (tab.highlight ? "text-purple-500" : "text-primary") : "text-default-400"
              }`}
            >
              <span className="text-lg">{tab.icon}</span>
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
