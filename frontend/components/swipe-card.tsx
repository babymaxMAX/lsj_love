"use client";
import { useState } from "react";
import { motion, useMotionValue, useTransform, PanInfo } from "framer-motion";
import { BackEnd_URL } from "@/config/url";

interface User {
    telegram_id: number;
    name: string;
    age: number;
    city: string;
    photo: string;
    about?: string;
    username?: string;
}

interface SwipeCardProps {
    user: User;
    userId: string;
    onLike: () => void;
    onDislike: () => void;
}

export function SwipeCard({ user, userId, onLike, onDislike }: SwipeCardProps) {
    const [icebreaker, setIcebreaker] = useState<string | null>(null);
    const [loadingIce, setLoadingIce] = useState(false);
    const [showAbout, setShowAbout] = useState(false);

    const x = useMotionValue(0);
    const rotate = useTransform(x, [-200, 200], [-25, 25]);
    const likeOpacity = useTransform(x, [0, 100], [0, 1]);
    const dislikeOpacity = useTransform(x, [-100, 0], [1, 0]);

    const handleDragEnd = (_: any, info: PanInfo) => {
        if (info.offset.x > 100) {
            onLike();
        } else if (info.offset.x < -100) {
            onDislike();
        }
    };

    const generateIcebreaker = async () => {
        setLoadingIce(true);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/ai/icebreaker`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sender_id: parseInt(userId), target_id: user.telegram_id }),
            });
            const data = await res.json();
            setIcebreaker(data.message);
        } catch {
            setIcebreaker("Привет! Твой профиль меня заинтересовал — расскажи о себе?");
        } finally {
            setLoadingIce(false);
        }
    };

    const copyToClipboard = () => {
        if (icebreaker) {
            navigator.clipboard.writeText(icebreaker);
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.showAlert("Скопировано! Отправь это сообщение в чате.");
            }
        }
    };

    return (
        <div className="relative w-full max-w-sm">
            {/* Индикаторы свайпа */}
            <motion.div
                style={{ opacity: likeOpacity }}
                className="absolute top-8 left-8 z-10 bg-green-500 text-white font-bold text-2xl px-4 py-2 rounded-xl rotate-[-15deg] border-4 border-green-600"
            >
                НРАВИТСЯ ❤️
            </motion.div>
            <motion.div
                style={{ opacity: dislikeOpacity }}
                className="absolute top-8 right-8 z-10 bg-red-500 text-white font-bold text-2xl px-4 py-2 rounded-xl rotate-[15deg] border-4 border-red-600"
            >
                ПРОПУСК 👎
            </motion.div>

            {/* Карточка */}
            <motion.div
                style={{ x, rotate }}
                drag="x"
                dragConstraints={{ left: 0, right: 0 }}
                onDragEnd={handleDragEnd}
                className="cursor-grab active:cursor-grabbing rounded-3xl overflow-hidden shadow-2xl bg-content1 select-none"
                whileTap={{ scale: 1.02 }}
            >
                {/* Фото */}
                <div className="relative">
                    <img
                        src={user.photo || "/placeholder.jpg"}
                        alt={user.name}
                        className="w-full h-96 object-cover"
                        draggable={false}
                    />
                    {/* Градиент */}
                    <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-black/80 to-transparent" />

                    {/* Инфо поверх фото */}
                    <div className="absolute bottom-4 left-4 right-4 text-white">
                        <div className="flex items-end justify-between">
                            <div>
                                <h2 className="text-2xl font-bold">{user.name}, {user.age}</h2>
                                <p className="text-sm opacity-80">📍 {user.city}</p>
                            </div>
                            {user.about && (
                                <button
                                    onClick={() => setShowAbout(!showAbout)}
                                    className="text-2xl hover:scale-110 transition-transform"
                                >
                                    ℹ️
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* О себе */}
                {showAbout && user.about && (
                    <div className="px-4 py-3 bg-content2">
                        <p className="text-sm text-default-600">{user.about}</p>
                    </div>
                )}

                {/* AI Icebreaker */}
                <div className="px-4 py-3">
                    {!icebreaker ? (
                        <button
                            onClick={generateIcebreaker}
                            disabled={loadingIce}
                            className="w-full py-2 px-4 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-60"
                        >
                            {loadingIce ? "⏳ Генерирую..." : "✨ AI Icebreaker — что написать?"}
                        </button>
                    ) : (
                        <div className="bg-content2 rounded-xl p-3">
                            <p className="text-sm text-default-700 mb-2">{icebreaker}</p>
                            <div className="flex gap-2">
                                <button
                                    onClick={copyToClipboard}
                                    className="flex-1 py-1.5 rounded-lg bg-primary text-white text-xs font-medium"
                                >
                                    📋 Скопировать
                                </button>
                                <button
                                    onClick={() => setIcebreaker(null)}
                                    className="py-1.5 px-3 rounded-lg bg-default-200 text-default-600 text-xs"
                                >
                                    ↩️
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </motion.div>

            {/* Кнопки лайк/дизлайк */}
            <div className="flex justify-center gap-8 mt-6">
                <button
                    onClick={onDislike}
                    className="w-16 h-16 rounded-full bg-content1 shadow-lg flex items-center justify-center text-2xl hover:scale-110 transition-transform border border-divider"
                >
                    👎
                </button>
                <button
                    onClick={onLike}
                    className="w-16 h-16 rounded-full bg-gradient-to-r from-pink-500 to-red-500 shadow-lg flex items-center justify-center text-2xl hover:scale-110 transition-transform"
                >
                    ❤️
                </button>
            </div>
        </div>
    );
}

declare global {
    interface Window {
        Telegram?: {
            WebApp: {
                showAlert: (message: string) => void;
            };
        };
    }
}
