"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";

interface TargetUser {
    telegram_id: number;
    name: string;
    username?: string;
    age?: number;
    city?: string;
    about?: string;
    photo?: string;
    photos: string[];
    gender?: string;
    looking_for?: string;
    last_seen?: string;
}

function getOnlineStatus(lastSeen?: string): { label: string; color: string; dot: string } {
    if (!lastSeen) return { label: "Не в сети", color: "rgba(255,255,255,0.4)", dot: "#6b7280" };
    const diff = Date.now() - new Date(lastSeen).getTime();
    const minutes = diff / 60000;
    if (minutes < 5) return { label: "Онлайн", color: "#86efac", dot: "#22c55e" };
    if (minutes < 60) return { label: `Был(а) ${Math.floor(minutes)} мин назад`, color: "#fcd34d", dot: "#f59e0b" };
    const hours = minutes / 60;
    if (hours < 24) return { label: `Был(а) ${Math.floor(hours)} ч назад`, color: "rgba(255,255,255,0.45)", dot: "#94a3b8" };
    return { label: "Был(а) давно", color: "rgba(255,255,255,0.3)", dot: "#6b7280" };
}

interface PhotoLikeState {
    count: number;
    liked_by_me: boolean;
}

export default function ViewProfilePage() {
    const params = useParams();
    const router = useRouter();
    const userId = params.users as string;
    const targetId = params.targetId as string;

    const [user, setUser] = useState<TargetUser | null>(null);
    const [loading, setLoading] = useState(true);
    const [currentPhoto, setCurrentPhoto] = useState(0);
    const [photoLikes, setPhotoLikes] = useState<Record<number, PhotoLikeState>>({});
    const [likeLoading, setLikeLoading] = useState(false);
    const [profileLiked, setProfileLiked] = useState(false);
    const [profileLikeLoading, setProfileLikeLoading] = useState(false);
    const [isMatch, setIsMatch] = useState(false);
    const [likeAnim, setLikeAnim] = useState(false);

    const touchStartX = useRef<number | null>(null);
    const touchStartY = useRef<number | null>(null);

    const photos: string[] = user?.photos?.length
        ? user.photos.map((p) => p.startsWith("http") ? p : `${BackEnd_URL}${p}`)
        : user?.photo
            ? [`${BackEnd_URL}/api/v1/users/${targetId}/photo`]
            : ["/placeholder.svg"];

    // Загружаем профиль
    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/users/${targetId}`)
            .then((r) => r.json())
            .then(setUser)
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, [targetId]);

    // Пинг: обновляем last_seen текущего пользователя
    useEffect(() => {
        if (!userId) return;
        const ping = () => fetch(`${BackEnd_URL}/api/v1/users/${userId}/ping`, { method: "POST" }).catch(() => {});
        ping();
        const interval = setInterval(ping, 60_000);
        return () => clearInterval(interval);
    }, [userId]);

    // Проверяем лайк и матч
    useEffect(() => {
        if (!userId || !targetId) return;
        fetch(`${BackEnd_URL}/api/v1/likes/${userId}/${targetId}`)
            .then((r) => r.json())
            .then((data) => { if (data.status === true) setProfileLiked(true); })
            .catch(() => {});
        fetch(`${BackEnd_URL}/api/v1/likes/matches/${userId}`)
            .then((r) => r.json())
            .then((data) => {
                const ids: number[] = (data.items ?? []).map((u: any) => u.telegram_id);
                if (ids.includes(parseInt(targetId))) setIsMatch(true);
            })
            .catch(() => {});
    }, [userId, targetId]);

    // Загружаем лайки для текущего фото
    const fetchPhotoLikes = useCallback(async (index: number) => {
        if (!userId) return;
        try {
            const res = await fetch(
                `${BackEnd_URL}/api/v1/photo-interactions/likes/${targetId}/${index}?viewer_id=${userId}`
            );
            if (res.ok) {
                const data = await res.json();
                setPhotoLikes((prev) => ({
                    ...prev,
                    [index]: { count: data.count, liked_by_me: data.liked_by_me },
                }));
            }
        } catch {}
    }, [targetId, userId]);

    useEffect(() => {
        if (user) fetchPhotoLikes(currentPhoto);
    }, [user, currentPhoto, fetchPhotoLikes]);

    const handlePhotoLike = async () => {
        if (likeLoading || !userId) return;
        setLikeLoading(true);
        // Оптимистичный UI — сразу показываем изменение
        const prev = photoLikes[currentPhoto] ?? { count: 0, liked_by_me: false };
        const optimistic: PhotoLikeState = {
            count: prev.liked_by_me ? prev.count - 1 : prev.count + 1,
            liked_by_me: !prev.liked_by_me,
        };
        setPhotoLikes((s) => ({ ...s, [currentPhoto]: optimistic }));
        if (!prev.liked_by_me) {
            setLikeAnim(true);
            setTimeout(() => setLikeAnim(false), 600);
        }
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/photo-interactions/likes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    from_user: parseInt(userId),
                    owner_id: parseInt(targetId),
                    photo_index: currentPhoto,
                }),
            });
            if (res.ok) {
                const data = await res.json();
                setPhotoLikes((s) => ({
                    ...s,
                    [currentPhoto]: { count: data.count, liked_by_me: data.liked_by_me },
                }));
            }
        } catch {} finally {
            setLikeLoading(false);
        }
    };

    const handleProfileLike = async () => {
        if (profileLikeLoading || profileLiked || isMatch || !userId) return;
        setProfileLikeLoading(true);
        try {
            await fetch(`${BackEnd_URL}/api/v1/likes/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ from_user: parseInt(userId), to_user: parseInt(targetId) }),
            });
            setProfileLiked(true);
        } catch {} finally {
            setProfileLikeLoading(false);
        }
    };

    const nextPhoto = () => setCurrentPhoto((p) => Math.min(p + 1, photos.length - 1));
    const prevPhoto = () => setCurrentPhoto((p) => Math.max(p - 1, 0));

    const handleTouchStart = (e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
        touchStartY.current = e.touches[0].clientY;
    };
    const handleTouchEnd = (e: React.TouchEvent) => {
        if (touchStartX.current === null || touchStartY.current === null) return;
        const dx = touchStartX.current - e.changedTouches[0].clientX;
        const dy = Math.abs(touchStartY.current - e.changedTouches[0].clientY);
        // Горизонтальный свайп (больше горизонтального движения чем вертикального)
        if (Math.abs(dx) > 40 && Math.abs(dx) > dy) {
            dx > 0 ? nextPhoto() : prevPhoto();
        }
        touchStartX.current = null;
        touchStartY.current = null;
    };

    const meta = photoLikes[currentPhoto];

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center" style={{ background: "#0f0f1a" }}>
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return (
            <div className="min-h-screen flex flex-col" style={{ background: "#0f0f1a" }}>
                <div
                    className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3"
                    style={{ background: "rgba(15,15,26,0.95)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(255,255,255,0.07)" }}
                >
                    <button
                        onClick={() => router.back()}
                        className="w-9 h-9 rounded-full flex items-center justify-center transition-all active:scale-90"
                        style={{ background: "rgba(255,255,255,0.1)" }}
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                            <path d="M19 12H5M12 5l-7 7 7 7"/>
                        </svg>
                    </button>
                    <p className="font-semibold text-white/80">Профиль</p>
                </div>
                <div className="flex flex-col items-center justify-center flex-1 gap-4 px-8 text-center">
                    <div className="text-5xl">😕</div>
                    <p className="text-white font-semibold text-lg">Профиль недоступен</p>
                    <p className="text-white/40 text-sm">Пользователь удалил аккаунт или скрыл профиль</p>
                    <button
                        onClick={() => router.back()}
                        className="mt-2 px-6 py-3 rounded-2xl font-semibold text-sm text-white transition-all active:scale-95"
                        style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)" }}
                    >
                        ← Назад
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen pb-10" style={{ background: "#0f0f1a", color: "#fff" }}>
            {/* Шапка */}
            <div
                className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3"
                style={{ background: "rgba(15,15,26,0.95)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(255,255,255,0.07)" }}
            >
                <button
                    onClick={() => router.back()}
                    className="w-9 h-9 rounded-full flex items-center justify-center transition-all active:scale-90"
                    style={{ background: "rgba(255,255,255,0.1)" }}
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                        <path d="M19 12H5M12 5l-7 7 7 7"/>
                    </svg>
                </button>
                <div>
                    <p className="font-bold text-base leading-tight">{user.name}{user.age ? `, ${user.age}` : ""}</p>
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
            </div>

            {/* Photo slider */}
            <div
                className="relative w-full"
                style={{ aspectRatio: "3/4", maxHeight: "65vh", background: "#111" }}
                onTouchStart={handleTouchStart}
                onTouchEnd={handleTouchEnd}
            >
                <img
                    key={photos[currentPhoto]}
                    src={photos[currentPhoto]}
                    alt={user.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                        const img = e.target as HTMLImageElement;
                        if (!img.src.endsWith("/placeholder.svg")) img.src = "/placeholder.svg";
                    }}
                />

                {/* Gradient */}
                <div
                    className="absolute inset-0"
                    style={{ background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.1) 50%, transparent 100%)" }}
                />

                {/* Progress bars */}
                {photos.length > 1 && (
                    <div className="absolute top-0 left-0 right-0 px-3 pt-2 z-10">
                        <div className="flex gap-1 mb-1">
                            {photos.map((_, i) => (
                                <div
                                    key={i}
                                    onClick={() => setCurrentPhoto(i)}
                                    className="rounded-full cursor-pointer transition-all duration-300"
                                    style={{
                                        height: 3,
                                        flex: 1,
                                        background: i === currentPhoto ? "#fff" : i < currentPhoto ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.22)",
                                    }}
                                />
                            ))}
                        </div>
                        <div className="flex justify-end">
                            <span style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(6px)", color: "rgba(255,255,255,0.85)", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 20 }}>
                                {currentPhoto + 1} / {photos.length}
                            </span>
                        </div>
                    </div>
                )}

                {/* Nav arrows */}
                {photos.length > 1 && currentPhoto > 0 && (
                    <button
                        onClick={prevPhoto}
                        className="absolute left-2 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center"
                        style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(6px)" }}
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
                    </button>
                )}
                {photos.length > 1 && currentPhoto < photos.length - 1 && (
                    <button
                        onClick={nextPhoto}
                        className="absolute right-2 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center"
                        style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(6px)" }}
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round"><path d="M9 18l6-6-6-6"/></svg>
                    </button>
                )}

                {/* PHOTO LIKE BUTTON — крупная кнопка в углу */}
                <div className="absolute bottom-4 right-4 z-20 flex flex-col items-center gap-1">
                    <button
                        onClick={handlePhotoLike}
                        disabled={likeLoading}
                        className="transition-all active:scale-90"
                        style={{
                            width: 56,
                            height: 56,
                            borderRadius: "50%",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: meta?.liked_by_me
                                ? "linear-gradient(135deg, #ef4444, #ec4899)"
                                : "rgba(255,255,255,0.18)",
                            backdropFilter: "blur(8px)",
                            boxShadow: meta?.liked_by_me
                                ? "0 4px 20px rgba(239,68,68,0.5)"
                                : "0 4px 12px rgba(0,0,0,0.3)",
                            border: meta?.liked_by_me ? "none" : "1.5px solid rgba(255,255,255,0.3)",
                            transform: likeAnim ? "scale(1.3)" : "scale(1)",
                            transition: "all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
                        }}
                    >
                        <svg
                            width="26"
                            height="26"
                            viewBox="0 0 24 24"
                            fill={meta?.liked_by_me ? "#fff" : "none"}
                            stroke={meta?.liked_by_me ? "#fff" : "rgba(255,255,255,0.9)"}
                            strokeWidth="2"
                        >
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                        </svg>
                    </button>
                    {/* Счётчик лайков */}
                    {meta && meta.count > 0 && (
                        <div
                            className="text-center"
                            style={{
                                background: "rgba(0,0,0,0.5)",
                                backdropFilter: "blur(6px)",
                                borderRadius: 12,
                                padding: "2px 8px",
                                minWidth: 36,
                            }}
                        >
                            <span className="text-white font-bold text-xs">{meta.count}</span>
                        </div>
                    )}
                </div>

                {/* Подсказка для множества фото */}
                {photos.length > 1 && (
                    <div className="absolute bottom-4 left-4 z-10">
                        <span style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)", color: "rgba(255,255,255,0.65)", fontSize: 11, padding: "3px 10px", borderRadius: 12 }}>
                            ← листай →
                        </span>
                    </div>
                )}

                {/* Имя / город */}
                <div className="absolute bottom-16 left-4 right-20 z-10">
                    <h1 className="text-2xl font-bold text-white drop-shadow-lg">
                        {user.name}{user.age ? `, ${user.age}` : ""}
                    </h1>
                    {user.city && (
                        <p className="text-white/75 text-sm mt-0.5">📍 {user.city}</p>
                    )}
                </div>
            </div>

            {/* Карточка информации */}
            <div className="px-4 pt-4 space-y-3">
                {/* О себе */}
                {user.about && (
                    <div
                        className="rounded-2xl p-4"
                        style={{ background: "rgba(255,255,255,0.06)" }}
                    >
                        <p className="text-xs text-white/40 font-semibold uppercase tracking-wider mb-2">О себе</p>
                        <p className="text-sm text-white/85 leading-relaxed">{user.about}</p>
                    </div>
                )}

                {/* ЛАЙКНУТЬ АНКЕТУ */}
                {isMatch ? (
                    <div
                        className="w-full py-4 rounded-2xl font-bold text-base text-center"
                        style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)", color: "#fff", boxShadow: "0 6px 24px rgba(236,72,153,0.35)" }}
                    >
                        💕 Взаимная симпатия — у вас матч!
                    </div>
                ) : (
                    <button
                        onClick={handleProfileLike}
                        disabled={profileLikeLoading || profileLiked}
                        className="w-full py-4 rounded-2xl font-bold text-base transition-all active:scale-95 disabled:opacity-70"
                        style={{
                            background: profileLiked
                                ? "rgba(255,255,255,0.08)"
                                : "linear-gradient(135deg, #7c3aed, #ec4899)",
                            color: "#fff",
                            boxShadow: profileLiked ? "none" : "0 6px 24px rgba(124,58,237,0.35)",
                        }}
                    >
                        {profileLikeLoading ? "⏳ Отправляем..." : profileLiked ? "✓ Симпатия отправлена" : "💌 Лайкнуть анкету"}
                    </button>
                )}

                {/* Написать (если есть username) */}
                {user.username && user.username.trim() && !isMatch && (
                    <a
                        href={`https://t.me/${user.username.trim()}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block w-full py-3.5 rounded-2xl font-semibold text-sm text-center transition-all active:scale-95"
                        style={{ background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.85)" }}
                    >
                        💬 Написать в Telegram
                    </a>
                )}
            </div>
        </div>
    );
}
