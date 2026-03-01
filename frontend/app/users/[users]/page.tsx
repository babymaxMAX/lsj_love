"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";
import { SwipeCard } from "@/components/swipe-card";
import { BottomNav } from "@/components/bottom-nav";
import { QuestionCard } from "@/components/question-card";

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

// @ts-ignore
export default function UsersPage({ params }: { params: { users: string } }) {
    const router = useRouter();
    const [users, setUsers] = useState<any[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [showQuestion, setShowQuestion] = useState(false);
    const [loading, setLoading] = useState(true);
    // IDs пролайканных в этой сессии — чтобы не показывать снова если бэк вернул их
    const [seenIds] = useState<Set<number>>(() => new Set());
    const [swipeCount, setSwipeCount] = useState(0);
    const [showProfileQuestion, setShowProfileQuestion] = useState(false);
    const [nextQuestion, setNextQuestion] = useState<any>(null);

    const loadUsers = useCallback(async () => {
        setLoading(true);
        const items = await fetchUsers(params.users);
        const fresh = items.filter((u: any) => !seenIds.has(u.telegram_id));
        setUsers(fresh);
        setCurrentIndex(0);
        setLoading(false);
    }, [params.users, seenIds]);

    useEffect(() => {
        loadUsers();
    }, [loadUsers]);

    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/profile/questions?telegram_id=${params.users}`)
            .then((r) => r.json())
            .then((d) => setNextQuestion(d.question || null))
            .catch(() => {});
    }, [params.users]);

    // Пинг: обновляем last_seen при открытии и каждые 60 секунд
    useEffect(() => {
        const ping = () => fetch(`${BackEnd_URL}/api/v1/users/${params.users}/ping`, { method: "POST" }).catch(() => {});
        ping();
        const interval = setInterval(ping, 60_000);
        return () => clearInterval(interval);
    }, [params.users]);

    // Перезагружаем только если анкеты закончились
    useEffect(() => {
        const onVisible = () => {
            if (document.visibilityState === "visible" && currentIndex >= users.length) {
                loadUsers();
            }
        };
        document.addEventListener("visibilitychange", onVisible);
        return () => document.removeEventListener("visibilitychange", onVisible);
    }, [loadUsers, currentIndex, users.length]);

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
        const newCount = swipeCount + 1;
        setSwipeCount(newCount);
        if (newCount % 5 === 0 && nextQuestion) {
            setShowProfileQuestion(true);
        } else {
            setCurrentIndex((prev) => prev + 1);
        }
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
                <h1 className="text-base font-bold" style={{ color: "#fff" }}>LSJLove 💕</h1>

                {/* Правая кнопка — Вопрос профиля */}
                <button
                    onClick={async () => {
                        if (!showQuestion && !nextQuestion) {
                            try {
                                const res = await fetch(`${BackEnd_URL}/api/v1/profile/questions?telegram_id=${params.users}`);
                                const d = await res.json();
                                if (d.question && !d.done) {
                                    setNextQuestion(d.question);
                                    setShowQuestion(true);
                                }
                            } catch {}
                        } else {
                            setShowQuestion(!showQuestion);
                        }
                    }}
                    className="absolute right-4 text-xl"
                    style={{ zIndex: 10 }}
                    title="Вопросы для профиля"
                >
                    {nextQuestion ? "❓" : "✅"}
                </button>
            </div>

            {/* Свайп карточки */}
            <div className="flex-1 flex items-center justify-center px-4 py-6">
                {(showProfileQuestion || showQuestion) && nextQuestion ? (
                    <QuestionCard
                        question={nextQuestion}
                        userId={params.users}
                        onDone={async () => {
                            const wasManual = showQuestion && !showProfileQuestion;
                            setShowQuestion(false);
                            setShowProfileQuestion(false);
                            setNextQuestion(null);
                            if (!wasManual) {
                                setCurrentIndex((prev) => prev + 1);
                            }
                            try {
                                const res = await fetch(`${BackEnd_URL}/api/v1/profile/questions?telegram_id=${params.users}`);
                                const d = await res.json();
                                if (d.question && !d.done) {
                                    setNextQuestion(d.question);
                                } else {
                                    setNextQuestion(null);
                                }
                            } catch {
                                setNextQuestion(null);
                            }
                        }}
                    />
                ) : currentUser ? (
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
