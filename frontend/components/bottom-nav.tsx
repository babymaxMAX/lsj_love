"use client";
import { useRouter, usePathname } from "next/navigation";
import { useCallback, useRef } from "react";

interface BottomNavProps {
    userId: string;
}

export function BottomNav({ userId }: BottomNavProps) {
    const router = useRouter();
    const pathname = usePathname();
    // Защита от двойного нажатия
    const navRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const tabs = [
        { icon: "🔥", label: "Анкеты", path: `/users/${userId}`, exact: true },
        { icon: "💌", label: "Матчи", path: `/users/${userId}/matches`, exact: false },
        { icon: "🧠", label: "AI Чат", path: `/users/${userId}/ai-advisor`, highlight: true, exact: false },
        { icon: "👤", label: "Профиль", path: `/users/${userId}/profile`, exact: false },
        { icon: "⭐", label: "Premium", path: `/users/${userId}/premium`, exact: false },
    ];

    const navigate = useCallback((path: string) => {
        if (navRef.current) return; // блокируем двойное нажатие
        navRef.current = setTimeout(() => { navRef.current = null; }, 800);
        router.push(path);
    }, [router]);

    return (
        <nav
            className="fixed bottom-0 left-0 right-0 bg-content1 border-t border-divider z-50"
            style={{ paddingBottom: "env(safe-area-inset-bottom)", touchAction: "manipulation" }}
        >
            <div className="max-w-lg mx-auto flex">
                {tabs.map((tab) => {
                    // Для корневого пути — точное совпадение; для остальных — prefix
                    const isActive = tab.exact
                        ? pathname === tab.path
                        : pathname === tab.path || pathname.startsWith(tab.path + "/");
                    return (
                        <button
                            key={tab.path}
                            onClick={() => navigate(tab.path)}
                            style={{ touchAction: "manipulation", userSelect: "none" }}
                            className={`flex-1 flex flex-col items-center py-2 gap-0.5 transition-colors relative select-none ${
                                isActive
                                    ? tab.highlight ? "text-purple-500" : "text-primary"
                                    : tab.highlight ? "text-purple-400/70" : "text-default-400"
                            }`}
                        >
                            {tab.highlight && !isActive && (
                                <span className="absolute top-1.5 right-1/4 w-1.5 h-1.5 bg-purple-500 rounded-full" />
                            )}
                            <span className="text-lg leading-none">{tab.icon}</span>
                            <span className="text-[10px] font-medium leading-tight">{tab.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
}
