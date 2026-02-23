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
        { icon: "👤", label: "Профиль", path: `/users/${userId}/profile` },
        { icon: "⭐", label: "Premium", path: `/users/${userId}/premium` },
    ];

    return (
        <nav className="fixed bottom-0 left-0 right-0 bg-content1 border-t border-divider z-50">
            <div className="max-w-lg mx-auto flex">
                {tabs.map((tab) => {
                    const isActive = pathname === tab.path;
                    return (
                        <button
                            key={tab.path}
                            onClick={() => router.push(tab.path)}
                            className={`flex-1 flex flex-col items-center py-3 gap-1 transition-colors ${
                                isActive
                                    ? "text-primary"
                                    : "text-default-400 hover:text-default-600"
                            }`}
                        >
                            <span className="text-xl">{tab.icon}</span>
                            <span className="text-xs font-medium">{tab.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
}
