"use client";
import React, { useEffect, useState } from "react";
import { BackEnd_URL } from "@/config/url";
import { SwipeCard } from "@/components/swipe-card";
import { BottomNav } from "@/components/bottom-nav";
import { DailyQuestion } from "@/components/daily-question";

const SKIPPED_KEY = (userId: string) => `skipped_${userId}`;
const LIKED_KEY = (userId: string) => `liked_${userId}`;

function getSkippedIds(userId: string): Set<number> {
    try {
        const raw = localStorage.getItem(SKIPPED_KEY(userId));
        return new Set(raw ? JSON.parse(raw) : []);
    } catch { return new Set(); }
}
function getLikedIds(userId: string): Set<number> {
    try {
        const raw = localStorage.getItem(LIKED_KEY(userId));
        return new Set(raw ? JSON.parse(raw) : []);
    } catch { return new Set(); }
}
function addSkipped(userId: string, targetId: number) {
    try {
        const ids = getSkippedIds(userId);
        ids.add(targetId);
        localStorage.setItem(SKIPPED_KEY(userId), JSON.stringify([...ids]));
    } catch {}
}
function addLiked(userId: string, targetId: number) {
    try {
        const ids = getLikedIds(userId);
        ids.add(targetId);
        localStorage.setItem(LIKED_KEY(userId), JSON.stringify([...ids]));
    } catch {}
}

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
    } catch {
        return null;
    }
}

// @ts-ignore
export default function UsersPage({ params }: { params: { users: string } }) {
    const [users, setUsers] = useState<any[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [dailyQuestion, setDailyQuestion] = useState<any>(null);
    const [showQuestion, setShowQuestion] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            fetchUsers(params.users),
            getDailyQuestion(),
        ]).then(([items, question]) => {
            // Фильтруем уже просмотренных из localStorage
            const skipped = getSkippedIds(params.users);
            const liked = getLikedIds(params.users);
            const seen = new Set([...skipped, ...liked]);
            const filtered = items.filter((u: any) => !seen.has(u.telegram_id));
            setUsers(filtered);
            setDailyQuestion(question);
            setLoading(false);
        });
    }, [params.users]);

    const handleLike = async (targetId: number) => {
        addLiked(params.users, targetId);
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
        addSkipped(params.users, targetId);
        nextUser();
    };

    const nextUser = () => {
        setCurrentIndex((prev) => prev + 1);
    };

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

    const currentUser = users[currentIndex];

    return (
        <div className="flex flex-col min-h-screen pb-20">
            {/* Заголовок */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-divider">
                <h1 className="text-xl font-bold text-primary">LSJLove 💕</h1>
                <button
                    onClick={() => setShowQuestion(!showQuestion)}
                    className="text-sm text-default-500 hover:text-primary transition-colors"
                >
                    💬 Вопрос дня
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
                        <p className="text-default-500 text-sm">
                            Мы показали тебе все подходящие профили. Возвращайся позже — появятся новые!
                        </p>
                    </div>
                )}
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}
