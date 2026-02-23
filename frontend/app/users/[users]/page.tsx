"use client";
import React, { useEffect, useState } from "react";
import { BackEnd_URL } from "@/config/url";
import { SwipeCard } from "@/components/swipe-card";
import { BottomNav } from "@/components/bottom-nav";
import { DailyQuestion } from "@/components/daily-question";

async function getUsers(user_id: string) {
    const res = await fetch(`${BackEnd_URL}/api/v1/users/best_result/${user_id}`, {
        cache: "no-store",
        headers: { "User-Agent": "Custom" },
    });
    if (!res.ok) return { items: [] };
    return res.json();
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
            getUsers(params.users),
            getDailyQuestion(),
        ]).then(([usersData, question]) => {
            setUsers(usersData.items || []);
            setDailyQuestion(question);
            setLoading(false);
        });
    }, [params.users]);

    const handleLike = async (targetId: number) => {
        try {
            await fetch(`${BackEnd_URL}/api/v1/likes/${params.users}/${targetId}`, {
                method: "POST",
            });
        } catch (e) {
            console.error(e);
        }
        nextUser();
    };

    const handleDislike = () => {
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
                        onDislike={handleDislike}
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
