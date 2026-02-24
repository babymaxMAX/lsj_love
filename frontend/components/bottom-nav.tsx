"use client";
import { useRouter, usePathname } from "next/navigation";

interface BottomNavProps {
    userId: string;
}

export function BottomNav({ userId }: BottomNavProps) {
    const router = useRouter();
    const pathname = usePathname();

    const tabs = [
        { icon: "🔥", label: "Анкеты", path: `/users/${userId}` },
        { icon: "💌", label: "Матчи", path: `/users/${userId}/matches` },
        { icon: "🧠", label: "AI Чат", path: `/users/${userId}/ai-advisor`, highlight: true },
        { icon: "👤", label: "Профиль", path: `/users/${userId}/profile` },
        { icon: "⭐", label: "Premium", path: `/users/${userId}/premium` },
    ];

    return (
        <nav className="fixed bottom-0 left-0 right-0 bg-content1 border-t border-divider z-50"
             style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
            <div className="max-w-lg mx-auto flex">
                {tabs.map((tab) => {
                    const isActive = pathname === tab.path || pathname.startsWith(tab.path + "/");
                    return (
                        <button
                            key={tab.path}
                            onClick={() => router.push(tab.path)}
                            className={`flex-1 flex flex-col items-center py-2 gap-0.5 transition-colors relative ${
                                isActive
                                    ? tab.highlight ? "text-purple-500" : "text-primary"
                                    : tab.highlight ? "text-purple-400/70 hover:text-purple-400" : "text-default-400 hover:text-default-600"
                            }`}
                        >
                            {tab.highlight && !isActive && (
                                <span className="absolute top-1.5 right-1/4 w-1.5 h-1.5 bg-purple-500 rounded-full" />
                            )}
                            <span className="text-lg">{tab.icon}</span>
                            <span className="text-[10px] font-medium leading-tight">{tab.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
}
