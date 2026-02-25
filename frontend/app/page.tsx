"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";

export default function RootPage() {
    const router = useRouter();
    const [status, setStatus] = useState<"loading" | "no_telegram" | "not_registered">("loading");

    useEffect(() => {
        const init = async () => {
            // Читаем ID из Telegram WebApp
            const tg = (window as any).Telegram?.WebApp;
            let userId: number | null = null;

            if (tg) {
                tg.ready();
                tg.expand();
                userId = tg.initDataUnsafe?.user?.id ?? null;
            }

            if (!userId) {
                setStatus("no_telegram");
                return;
            }

            // Проверяем зарегистрирован ли пользователь
            try {
                const res = await fetch(`${BackEnd_URL}/api/v1/users/${userId}`);
                if (res.ok) {
                    const user = await res.json();
                    // Перенаправляем если пользователь найден в БД (is_active может быть false у старых аккаунтов)
                    if (user && user.telegram_id) {
                        router.replace(`/users/${userId}`);
                        return;
                    }
                }
                // Не зарегистрирован — показываем подсказку
                setStatus("not_registered");
            } catch {
                setStatus("not_registered");
            }
        };

        init();
    }, []);

    if (status === "loading") {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-4">
                <div className="text-5xl animate-pulse">💕</div>
                <p className="text-default-500 text-sm">Загружаем LSJLove...</p>
            </div>
        );
    }

    if (status === "not_registered") {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-6 px-8 text-center">
                <div className="text-6xl">🤗</div>
                <h1 className="text-2xl font-bold">Добро пожаловать!</h1>
                <p className="text-default-500">
                    Чтобы начать, напиши боту <strong>/start</strong> и заполни анкету.
                </p>
                <p className="text-sm text-default-400">
                    После регистрации открой приложение снова.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-6 px-8 text-center">
            <div className="text-6xl">💕</div>
            <h1 className="text-2xl font-bold">LSJLove</h1>
            <p className="text-default-500">
                Открой это приложение через бота Telegram.
            </p>
        </div>
    );
}
