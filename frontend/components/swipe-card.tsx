"use client";
import { useState, useEffect, useCallback } from "react";
import { motion, useMotionValue, useTransform, PanInfo } from "framer-motion";
import { BackEnd_URL } from "@/config/url";
import { PhotoLikeButton } from "@/components/photo-like-button";

interface User {
    telegram_id: number;
    name: string;
    age: number;
    city: string;
    photo: string;
    photos?: string[];
    about?: string;
    username?: string;
    last_seen?: string;
}

function getOnlineStatus(lastSeen?: string | null): { label: string; color: string; dot: string } {
    if (!lastSeen) return { label: "Не в сети", color: "rgba(255,255,255,0.35)", dot: "#6b7280" };
    // Если нет timezone — добавляем Z чтобы JS не трактовал как локальное время
    const ls = lastSeen.includes("+") || lastSeen.endsWith("Z") ? lastSeen : lastSeen + "Z";
    const diff = Date.now() - new Date(ls).getTime();
    if (isNaN(diff)) return { label: "Не в сети", color: "rgba(255,255,255,0.35)", dot: "#6b7280" };
    const minutes = diff / 60000;
    if (minutes < 5) return { label: "Онлайн", color: "#86efac", dot: "#22c55e" };
    if (minutes < 60) return { label: `${Math.floor(minutes)} мин назад`, color: "#fcd34d", dot: "#f59e0b" };
    const hours = minutes / 60;
    if (hours < 24) return { label: `${Math.floor(hours)} ч назад`, color: "rgba(255,255,255,0.4)", dot: "#94a3b8" };
    return { label: "Давно", color: "rgba(255,255,255,0.25)", dot: "#6b7280" };
}

interface SwipeCardProps {
    user: User;
    userId: string;
    onLike: () => void;
    onDislike: () => void;
}

const TOPICS = [
    { id: "humor",      emoji: "😄", label: "Шутка",           desc: "Лёгкий юмор по профилю" },
    { id: "compliment", emoji: "💫", label: "Комплимент",       desc: "Что именно зацепило" },
    { id: "intrigue",   emoji: "🧩", label: "Интрига",          desc: "Вызвать любопытство" },
    { id: "common",     emoji: "🌍", label: "Найти общее",      desc: "Город, интересы" },
    { id: "direct",     emoji: "🔥", label: "Прямолинейно",     desc: "Честно и смело" },
];

type IceStep = "idle" | "topic" | "loading" | "variants" | "sent" | "locked";

const STORAGE_KEY = (userId: string) => `ice_uses_left_${userId}`;

export function SwipeCard({ user, userId, onLike, onDislike }: SwipeCardProps) {
    const [showAbout, setShowAbout] = useState(false);
    const [currentPhotoIdx, setCurrentPhotoIdx] = useState(0);
    const [iceStep, setIceStep] = useState<IceStep>("idle");
    const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
    const [variants, setVariants] = useState<string[]>([]);
    const [selectedVariant, setSelectedVariant] = useState<string | null>(null);
    const [usesLeft, setUsesLeft] = useState<number | null>(null);
    const [sending, setSending] = useState(false);

    const [photoLikeData, setPhotoLikeData] = useState<Record<number, { count: number; liked: boolean }>>({});

    useEffect(() => {
        const idx = currentPhotoIdx;
        if (photoLikeData[idx] !== undefined) return;
        fetch(`${BackEnd_URL}/api/v1/photo-interactions/likes/${user.telegram_id}/${idx}?viewer_id=${userId}`)
            .then((r) => r.ok ? r.json() : null)
            .then((d) => d && setPhotoLikeData((prev) => ({ ...prev, [idx]: { count: d.count, liked: d.liked_by_me } })))
            .catch(() => {});
    }, [user.telegram_id, userId, currentPhotoIdx, photoLikeData]);

    const x = useMotionValue(0);
    const rotate = useTransform(x, [-200, 200], [-25, 25]);
    const likeOpacity = useTransform(x, [0, 100], [0, 1]);
    const dislikeOpacity = useTransform(x, [-100, 0], [1, 0]);

    const handleDragEnd = (_: any, info: PanInfo) => {
        if (info.offset.x > 100) onLike();
        else if (info.offset.x < -100) onDislike();
    };

    // Загружаем статус из localStorage / backend при монтировании
    useEffect(() => {
        const cached = localStorage.getItem(STORAGE_KEY(userId));
        if (cached !== null) {
            setUsesLeft(parseInt(cached, 10));
        } else {
            fetch(`${BackEnd_URL}/api/v1/ai/icebreaker/status/${userId}`)
                .then((r) => r.json())
                .then((d) => {
                    const left = d.uses_left ?? 5;
                    setUsesLeft(left);
                    localStorage.setItem(STORAGE_KEY(userId), String(left));
                })
                .catch(() => setUsesLeft(5));
        }
    }, [userId]);

    const handleIcebreakerClick = () => {
        if (usesLeft === 0) {
            setIceStep("locked");
            return;
        }
        setIceStep("topic");
        setSelectedTopic(null);
        setVariants([]);
        setSelectedVariant(null);
    };

    const handleTopicSelect = async (topicId: string) => {
        setSelectedTopic(topicId);
        setIceStep("loading");

        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/ai/icebreaker`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sender_id: parseInt(userId),
                    target_id: user.telegram_id,
                    topic: topicId,
                }),
            });

            if (res.status === 403) {
                setUsesLeft(0);
                localStorage.setItem(STORAGE_KEY(userId), "0");
                setIceStep("locked");
                return;
            }

            const data = await res.json();
            const newLeft = data.uses_left ?? 0;
            setUsesLeft(newLeft);
            localStorage.setItem(STORAGE_KEY(userId), String(newLeft));

            const v: string[] = data.variants || [];
            if (v.length > 0) {
                setVariants(v);
                setIceStep("variants");
            } else {
                setIceStep("idle");
            }
        } catch {
            setIceStep("idle");
        }
    };

    const handleSend = async () => {
        if (!selectedVariant) return;
        setSending(true);
        try {
            await fetch(`${BackEnd_URL}/api/v1/ai/icebreaker/send`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sender_id: parseInt(userId),
                    target_id: user.telegram_id,
                    message: selectedVariant,
                }),
            });
            setIceStep("sent");
        } catch {
            setIceStep("variants");
        } finally {
            setSending(false);
        }
    };

    const resetIce = () => {
        setIceStep("idle");
        setSelectedTopic(null);
        setVariants([]);
        setSelectedVariant(null);
    };

    const handleSuperlike = async () => {
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/likes/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    from_user: parseInt(userId),
                    to_user: user.telegram_id,
                    is_superlike: true,
                }),
            });
            if (res.status === 403) {
                const data = await res.json();
                const msg = data?.detail?.error || "Нет суперлайков. Купи суперлайк в разделе Premium.";
                if (typeof window !== "undefined" && window.Telegram?.WebApp?.showAlert) {
                    window.Telegram.WebApp.showAlert(msg);
                } else {
                    alert(msg);
                }
                return;
            }
            // Суперлайк засчитан — переходим к следующей анкете
            onLike();
        } catch {
            onLike();
        }
    };

    // ─── Icebreaker overlay ────────────────────────────────────────────────────
    const renderIceOverlay = () => {
        if (iceStep === "idle") return null;

        return (
            <div
                className="absolute inset-0 z-20 rounded-3xl overflow-hidden flex flex-col"
                style={{ background: "rgba(0,0,0,0.92)" }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Закрыть */}
                <button
                    onClick={resetIce}
                    className="absolute top-3 right-3 text-white/60 text-2xl hover:text-white z-30"
                >
                    ✕
                </button>

                {/* Шаг: выбор темы */}
                {iceStep === "topic" && (
                    <div className="flex flex-col h-full p-5 pt-8">
                        <p className="text-white font-bold text-base mb-1">
                            ✨ AI Icebreaker
                        </p>
                        <p className="text-white/60 text-xs mb-4">
                            Выбери тему первого сообщения для {user.name}
                        </p>
                        <div className="flex flex-col gap-2 flex-1 overflow-y-auto">
                            {TOPICS.map((t) => (
                                <button
                                    key={t.id}
                                    onClick={() => handleTopicSelect(t.id)}
                                    className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-white/10 hover:bg-white/20 active:scale-95 transition-all text-left"
                                >
                                    <span className="text-2xl">{t.emoji}</span>
                                    <div>
                                        <p className="text-white font-semibold text-sm">{t.label}</p>
                                        <p className="text-white/50 text-xs">{t.desc}</p>
                                    </div>
                                </button>
                            ))}
                        </div>
                        {usesLeft !== null && (
                            <p className="text-white/40 text-xs text-center mt-3">
                                Осталось: {usesLeft} из 5 бесплатных
                            </p>
                        )}
                    </div>
                )}

                {/* Шаг: загрузка */}
                {iceStep === "loading" && (
                    <div className="flex flex-col items-center justify-center h-full gap-4 p-6">
                        <div className="text-5xl animate-bounce">🤖</div>
                        <p className="text-white font-semibold text-base text-center">
                            ИИ изучает профиль {user.name}...
                        </p>
                        <p className="text-white/50 text-xs text-center">
                            Анализирую фото, описание и подбираю слова
                        </p>
                        <div className="flex gap-1 mt-2">
                            {[0, 1, 2].map((i) => (
                                <div
                                    key={i}
                                    className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                                    style={{ animationDelay: `${i * 0.15}s` }}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Шаг: варианты */}
                {iceStep === "variants" && (
                    <div className="flex flex-col h-full p-4 pt-8">
                        <p className="text-white font-bold text-sm mb-1">
                            ✨ Выбери сообщение
                        </p>
                        <p className="text-white/50 text-xs mb-3">
                            Нажми на понравившееся
                        </p>
                        <div className="flex flex-col gap-2 flex-1 overflow-y-auto">
                            {variants.map((v, i) => (
                                <button
                                    key={i}
                                    onClick={() => setSelectedVariant(v)}
                                    className={`text-left px-4 py-3 rounded-2xl text-sm transition-all active:scale-95 ${
                                        selectedVariant === v
                                            ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/30"
                                            : "bg-white/10 text-white/90 hover:bg-white/20"
                                    }`}
                                >
                                    <span className="text-white/40 text-xs mr-1">{i + 1}.</span> {v}
                                </button>
                            ))}
                        </div>
                        <button
                            onClick={handleSend}
                            disabled={!selectedVariant || sending}
                            className={`mt-3 py-3 rounded-2xl font-semibold text-sm transition-all ${
                                selectedVariant && !sending
                                    ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg"
                                    : "bg-white/10 text-white/30 cursor-not-allowed"
                            }`}
                        >
                            {sending ? "⏳ Отправляем..." : "💌 Отправить сообщение"}
                        </button>
                    </div>
                )}

                {/* Шаг: успех */}
                {iceStep === "sent" && (
                    <div className="flex flex-col items-center justify-center h-full gap-4 p-6 text-center">
                        <div className="text-6xl">💌</div>
                        <p className="text-white font-bold text-lg">
                            Сообщение отправлено!
                        </p>
                        <p className="text-white/60 text-sm">
                            {user.name} получит уведомление в бот.
                            Если ответит — это матч 💕
                        </p>
                        <button
                            onClick={onLike}
                            className="mt-2 px-6 py-2 rounded-xl bg-gradient-to-r from-pink-500 to-red-500 text-white text-sm font-medium"
                        >
                            ❤️ Лайкнуть тоже
                        </button>
                        <button
                            onClick={onDislike}
                            className="px-6 py-2 rounded-xl bg-white/10 text-white/60 text-sm"
                        >
                            Следующий профиль →
                        </button>
                    </div>
                )}

                {/* Шаг: лимит исчерпан */}
                {iceStep === "locked" && (
                    <div className="flex flex-col items-center justify-center h-full gap-4 p-6 text-center">
                        <div className="text-5xl">🔒</div>
                        <p className="text-white font-bold text-base">
                            Бесплатные Icebreakers закончились
                        </p>
                        <p className="text-white/60 text-sm">
                            Ты использовал все 5 бесплатных попыток.
                            Получи больше с подпиской или купи пак.
                        </p>
                        <button
                            onClick={resetIce}
                            className="mt-2 px-6 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white text-sm font-medium"
                        >
                            ⭐ Получить Premium
                        </button>
                        <button
                            onClick={resetIce}
                            className="px-6 py-2 rounded-xl bg-white/10 text-white/60 text-sm"
                        >
                            Закрыть
                        </button>
                    </div>
                )}
            </div>
        );
    };

    // ─── Кнопка Icebreaker (в карточке) ──────────────────────────────────────
    const renderIcebreakerButton = () => {
        const left = usesLeft;
        const isLocked = left === 0;

        return (
            <button
                onClick={handleIcebreakerClick}
                className={`w-full py-2 px-4 rounded-xl text-white text-sm font-medium transition-all active:scale-95 ${
                    isLocked
                        ? "bg-white/20 opacity-70"
                        : "bg-gradient-to-r from-purple-500 to-pink-500 hover:opacity-90 shadow-md shadow-purple-500/30"
                }`}
            >
                {isLocked
                    ? "🔒 AI Icebreaker — нужна подписка"
                    : left !== null
                    ? `✨ AI Icebreaker (осталось ${left})`
                    : "✨ AI Icebreaker — что написать?"}
            </button>
        );
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
                drag={iceStep === "idle" ? "x" : false}
                dragConstraints={{ left: 0, right: 0 }}
                onDragEnd={handleDragEnd}
                className="relative cursor-grab active:cursor-grabbing rounded-3xl overflow-hidden shadow-2xl bg-content1 select-none"
                whileTap={iceStep === "idle" ? { scale: 1.02 } : {}}
            >
                {/* Overlay icebreaker */}
                {renderIceOverlay()}

                {/* Фото (слайдер) */}
                {(() => {
                    // Строим массив URL для фото
                    const photoUrls: string[] = [];
                    if (user.photos?.length) {
                        user.photos.forEach((p) => {
                            photoUrls.push(p.startsWith("http") ? p : `${BackEnd_URL}${p}`);
                        });
                    } else if (user.photo) {
                        photoUrls.push(`${BackEnd_URL}/api/v1/users/${user.telegram_id}/photo`);
                    } else {
                        photoUrls.push("/placeholder.svg");
                    }
                    const safeIdx = Math.min(currentPhotoIdx, photoUrls.length - 1);
                    return (
                        <div className="relative">
                            {/* Photo progress bars + counter */}
                            {photoUrls.length > 1 && (
                                <div className="absolute top-0 left-0 right-0 z-20 px-3 pt-2">
                                    <div className="flex gap-1 mb-1">
                                        {photoUrls.map((_, i) => (
                                            <div
                                                key={i}
                                                className="rounded-full transition-all duration-300"
                                                style={{
                                                    height: 3,
                                                    flex: 1,
                                                    background: i === safeIdx
                                                        ? "#fff"
                                                        : i < safeIdx
                                                        ? "rgba(255,255,255,0.6)"
                                                        : "rgba(255,255,255,0.25)",
                                                }}
                                            />
                                        ))}
                                    </div>
                                    <div className="flex justify-end">
                                        <span className="text-white/70 text-xs font-medium bg-black/30 backdrop-blur-sm px-2 py-0.5 rounded-full">
                                            {safeIdx + 1} / {photoUrls.length}
                                        </span>
                                    </div>
                                </div>
                            )}

                            <img
                                src={photoUrls[safeIdx]}
                                alt={user.name}
                                className="w-full h-96 object-cover"
                                draggable={false}
                                onError={(e) => {
                                    const img = e.target as HTMLImageElement;
                                    if (!img.src.endsWith("/placeholder.svg")) {
                                        img.src = "/placeholder.svg";
                                    }
                                }}
                            />

                            {/* Tap zones with visible edge indicators */}
                            {photoUrls.length > 1 && (
                                <>
                                    <motion.div
                                        className="absolute left-0 top-0 w-1/2 h-full z-10 flex items-center justify-start pl-2"
                                        onTap={() => setCurrentPhotoIdx((p) => (p - 1 + photoUrls.length) % photoUrls.length)}
                                    >
                                        {safeIdx > 0 && (
                                            <div className="w-7 h-7 rounded-full bg-black/30 backdrop-blur-sm flex items-center justify-center">
                                                <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
                                                    <path d="M15 18l-6-6 6-6" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
                                                </svg>
                                            </div>
                                        )}
                                    </motion.div>
                                    <motion.div
                                        className="absolute right-0 top-0 w-1/2 h-full z-10 flex items-center justify-end pr-2"
                                        onTap={() => setCurrentPhotoIdx((p) => (p + 1) % photoUrls.length)}
                                    >
                                        {safeIdx < photoUrls.length - 1 && (
                                            <div className="w-7 h-7 rounded-full bg-black/30 backdrop-blur-sm flex items-center justify-center">
                                                <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
                                                    <path d="M9 18l6-6-6-6" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
                                                </svg>
                                            </div>
                                        )}
                                    </motion.div>
                                </>
                            )}

                            <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-black/80 to-transparent" />

                            {/* Photo Like Button */}
                            <div style={{ position: "absolute", bottom: 80, left: 12, zIndex: 15 }}>
                                <PhotoLikeButton
                                    ownerId={user.telegram_id}
                                    photoIndex={safeIdx}
                                    viewerId={parseInt(userId)}
                                    initialLikes={photoLikeData[safeIdx]?.count ?? 0}
                                    initialLiked={photoLikeData[safeIdx]?.liked ?? false}
                                />
                            </div>

                            <div className="absolute bottom-4 left-4 right-4 text-white">
                                <div className="flex items-end justify-between">
                                    <div>
                                        <h2 className="text-2xl font-bold">{user.name}, {user.age}</h2>
                                        <p className="text-sm opacity-80">📍 {user.city}</p>
                                        {/* Онлайн-статус */}
                                        {(() => {
                                            const s = getOnlineStatus(user.last_seen);
                                            return (
                                                <div className="flex items-center gap-1 mt-0.5">
                                                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.dot }} />
                                                    <span className="text-xs font-medium" style={{ color: s.color }}>{s.label}</span>
                                                </div>
                                            );
                                        })()}
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
                    );
                })()}

                {/* О себе */}
                {showAbout && user.about && (
                    <div className="px-4 py-3 bg-content2">
                        <p className="text-sm text-default-600">{user.about}</p>
                    </div>
                )}

                {/* AI Icebreaker кнопка */}
                <div className="px-4 py-3">
                    {renderIcebreakerButton()}
                </div>
            </motion.div>

            {/* Кнопки лайк/дизлайк/суперлайк */}
            <div className="flex justify-center gap-5 mt-6">
                <button
                    onClick={onDislike}
                    className="w-16 h-16 rounded-full shadow-lg flex items-center justify-center text-2xl hover:scale-110 transition-transform border"
                    style={{ background: "rgba(255,255,255,0.08)", borderColor: "rgba(255,255,255,0.1)" }}
                >
                    👎
                </button>
                <button
                    onClick={handleSuperlike}
                    title="Суперлайк"
                    className="w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-xl hover:scale-110 transition-transform self-center"
                    style={{ background: "linear-gradient(135deg, #f59e0b, #f97316)", boxShadow: "0 4px 15px rgba(245,158,11,0.4)" }}
                >
                    ⭐
                </button>
                <button
                    onClick={onLike}
                    className="w-16 h-16 rounded-full shadow-lg flex items-center justify-center text-2xl hover:scale-110 transition-transform"
                    style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)", boxShadow: "0 4px 15px rgba(236,72,153,0.4)" }}
                >
                    ❤️
                </button>
            </div>

            {/* Подсказка суперлайка */}
            <p className="text-center text-xs mt-2" style={{ color: "rgba(255,255,255,0.3)" }}>
                ⭐ Суперлайк уведомит {user.name} и покажет твой профиль первым
            </p>
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
