"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";
import { SwipeCard } from "@/components/swipe-card";
import { BottomNav } from "@/components/bottom-nav";
import { DailyQuestion } from "@/components/daily-question";

async function fetchUsers(user_id: string) {
    try {
        const res = await fetch(`${BackEnd_URL}/api/v1/users/best_result/${user_id}`, {
            cache: "no-store",
            headers: { "User-Agent": "Custom" },
        });
        if (!res.ok) return [];
        const data = await res.json();
        return data.items || [];
    } catch { return []; }
}

async function getDailyQuestion() {
    try {
        const res = await fetch(`${BackEnd_URL}/api/v1/gamification/daily-question`, {
            cache: "no-store",
        });
        if (!res.ok) return null;
        return res.json();
    } catch { return null; }
}

// @ts-ignore
export default function UsersPage({ params }: { params: { users: string } }) {
    const router = useRouter();
    const [users, setUsers] = useState<any[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [dailyQuestion, setDailyQuestion] = useState<any>(null);
    const [showQuestion, setShowQuestion] = useState(false);
    const [loading, setLoading] = useState(true);
    // IDs пролайканных в этой сессии — чтобы не показывать снова если бэк вернул их
    const [seenIds] = useState<Set<number>>(() => new Set());

    const loadUsers = useCallback(async () => {
        setLoading(true);
        const [items, question] = await Promise.all([
            fetchUsers(params.users),
            getDailyQuestion(),
        ]);
        // Фильтруем только тех кого лайкнули/дизлайкнули В ЭТОЙ сессии
        const fresh = items.filter((u: any) => !seenIds.has(u.telegram_id));
        setUsers(fresh);
        setCurrentIndex(0);
        setDailyQuestion(question);
        setLoading(false);
    }, [params.users, seenIds]);

    useEffect(() => {
        loadUsers();
    }, [loadUsers]);

    // Пинг: обновляем last_seen при открытии и каждые 60 секунд
    useEffect(() => {
        const ping = () => fetch(`${BackEnd_URL}/api/v1/users/${params.users}/ping`, { method: "POST" }).catch(() => {});
        ping();
        const interval = setInterval(ping, 60_000);
        return () => clearInterval(interval);
    }, [params.users]);

    // Перезагружаем анкеты когда возвращаемся на страницу
    useEffect(() => {
        const onVisible = () => {
            if (document.visibilityState === "visible") loadUsers();
        };
        document.addEventListener("visibilitychange", onVisible);
        return () => document.removeEventListener("visibilitychange", onVisible);
    }, [loadUsers]);

    const [likeError, setLikeError] = useState<string | null>(null);

    const handleLike = async (targetId: number) => {
        seenIds.add(targetId);
        setLikeError(null);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/likes/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ from_user: parseInt(params.users), to_user: targetId }),
            });
            if (res.status === 403) {
                const data = await res.json().catch(() => ({}));
                const errMsg = data?.detail?.error || "Лимит лайков на сегодня исчерпан. Оформи Premium для безлимитных лайков.";
                setLikeError(errMsg);
                setTimeout(() => setLikeError(null), 5000);
                // Не переходим к следующей анкете при лимите
                return;
            }
        } catch (e) {
            console.error(e);
        }
        nextUser();
    };

    const handleDislike = async (targetId: number) => {
        seenIds.add(targetId);
        // Сохраняем дизлайк в БД — профиль не покажется снова даже после перезагрузки
        try {
            await fetch(`${BackEnd_URL}/api/v1/likes/dislike`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ from_user: parseInt(params.users), to_user: targetId }),
            });
        } catch { /* не критично */ }
        nextUser();
    };

    const nextUser = () => {
        setCurrentIndex((prev) => prev + 1);
    };

    const currentUser = users[currentIndex];

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen" style={{ background: "#0f0f1a" }}>
                <div className="text-center">
                    <div className="text-4xl mb-4">💕</div>
                    <p style={{ color: "rgba(255,255,255,0.5)" }}>Ищем людей рядом...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-screen pb-20" style={{ background: "#0f0f1a", color: "#fff" }}>
            {/* Заголовок — всегда видимый, прилипает к верху */}
            <div
                className="relative flex items-center justify-center px-4 py-3 flex-shrink-0"
                style={{ background: "#18182a", borderBottom: "1px solid rgba(255,255,255,0.08)", position: "sticky", top: 0, zIndex: 50 }}
            >
                {/* Левая кнопка — AI Подбор */}
                <button
                    onClick={() => router.push(`/users/${params.users}/ai-matchmaking`)}
                    className="absolute left-3 flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-bold transition-all active:scale-95"
                    style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)", color: "#fff", zIndex: 10 }}
                >
                    🤖 AI Подбор
                </button>

                {/* Центр — логотип */}
                <h1 className="text-base font-bold" style={{ color: "#fff" }}>Kupidon AI 💕</h1>

                {/* Правая кнопка — Вопрос дня */}
                <button
                    onClick={() => setShowQuestion(!showQuestion)}
                    className="absolute right-4 text-xl"
                    style={{ zIndex: 10 }}
                >
                    💬
                </button>
            </div>

            {/* Вопрос дня */}
            {showQuestion && dailyQuestion && (
                <DailyQuestion
                    question={dailyQuestion.question}
                    userId={params.users}
                    onClose={() => setShowQuestion(false)}
                />
            )}

            {/* Сообщение об ошибке лайка */}
            {likeError && (
                <div style={{
                    position: "fixed", top: 70, left: "50%", transform: "translateX(-50%)",
                    background: "#7c3aed", color: "#fff", borderRadius: 12, padding: "10px 20px",
                    fontSize: 13, fontWeight: 600, zIndex: 100, maxWidth: "90vw", textAlign: "center",
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                }}>
                    ❤️ {likeError}
                </div>
            )}

            {/* Свайп карточки */}
            <div className="flex-1 flex items-center justify-center px-4 py-6">
                {currentUser ? (
                    <SwipeCard
                        user={currentUser}
                        userId={params.users}
                        onLike={() => handleLike(currentUser.telegram_id)}
                        onDislike={() => handleDislike(currentUser.telegram_id)}
                    />
                ) : (
                    <div className="text-center px-8">
                        <div className="text-6xl mb-6">😔</div>
                        <h2 className="text-xl font-semibold mb-2" style={{ color: "#fff" }}>Анкеты закончились</h2>
                        <p className="text-sm mb-4" style={{ color: "rgba(255,255,255,0.5)" }}>
                            Ты просмотрел все профили. Возвращайся позже — появятся новые!
                        </p>
                        <button
                            onClick={loadUsers}
                            className="px-6 py-3 rounded-2xl text-white font-semibold text-sm transition-all active:scale-95 mb-3 block w-full"
                            style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
                        >
                            🔄 Обновить анкеты
                        </button>
                        <button
                            onClick={() => router.push(`/users/${params.users}/ai-matchmaking`)}
                            className="px-6 py-3 rounded-2xl text-white font-semibold text-sm transition-all active:scale-95 block w-full"
                            style={{ background: "rgba(124,58,237,0.3)", border: "1px solid rgba(124,58,237,0.5)" }}
                        >
                            🤖 AI Подбор партнёра
                        </button>
                    </div>
                )}
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}
