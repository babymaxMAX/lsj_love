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

    const handleLike = async (targetId: number) => {
        seenIds.add(targetId);
        try {
            await fetch(`${BackEnd_URL}/api/v1/likes/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ from_user: parseInt(params.users), to_user: targetId }),
            });
        } catch (e) {
            console.error(e);
        }
        nextUser();
    };

    const handleDislike = (targetId: number) => {
        seenIds.add(targetId); // не показывать снова в этой сессии
        nextUser();
    };

    const nextUser = () => {
        setCurrentIndex((prev) => prev + 1);
    };

    const currentUser = users[currentIndex];

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="text-4xl mb-4">💕</div>
                    <p className="text-default-500">Ищем людей рядом...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-screen pb-20">
            {/* Заголовок */}
            <div className="relative flex items-center justify-center px-4 py-3 border-b border-divider">
                {/* Левая кнопка — AI Подбор */}
                <button
                    onClick={() => router.push(`/users/${params.users}/ai-matchmaking`)}
                    className="absolute left-4 flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all active:scale-95"
                    style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)", color: "#fff" }}
                >
                    🤖 <span>AI Подбор</span>
                </button>

                {/* Центр — логотип */}
                <h1 className="text-xl font-bold text-primary">LSJLove 💕</h1>

                {/* Правая кнопка — Вопрос дня */}
                <button
                    onClick={() => setShowQuestion(!showQuestion)}
                    className="absolute right-4 text-xl transition-colors"
                    title="Вопрос дня"
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
                        <h2 className="text-xl font-semibold mb-2">Анкеты закончились</h2>
                        <p className="text-default-500 text-sm mb-6">
                            Ты просмотрел все профили. Возвращайся позже — появятся новые!
                        </p>
                        <button
                            onClick={loadUsers}
                            className="px-6 py-3 rounded-2xl text-white font-semibold text-sm transition-all active:scale-95"
                            style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
                        >
                            🔄 Обновить
                        </button>
                    </div>
                )}
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}
