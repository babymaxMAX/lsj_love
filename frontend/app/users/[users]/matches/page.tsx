"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";
import { BottomNav } from "@/components/bottom-nav";

interface MatchUser {
    telegram_id: number;
    name: string;
    age: number;
    city: string;
    photo: string;
    photos?: string[];
    media_types?: string[];
    username?: string;
    about?: string;
    last_seen?: string;
}

function getOnlineStatus(lastSeen?: string | null): { label: string; color: string; dot: string; isOnline: boolean } {
    if (!lastSeen) return { label: "Не в сети", color: "rgba(255,255,255,0.35)", dot: "#6b7280", isOnline: false };
    const ls = lastSeen.includes("+") || lastSeen.endsWith("Z") ? lastSeen : lastSeen + "Z";
    const diff = Date.now() - new Date(ls).getTime();
    if (isNaN(diff)) return { label: "Не в сети", color: "rgba(255,255,255,0.35)", dot: "#6b7280", isOnline: false };
    const minutes = diff / 60000;
    if (minutes < 5) return { label: "Онлайн", color: "#86efac", dot: "#22c55e", isOnline: true };
    if (minutes < 60) return { label: `Был(а) ${Math.floor(minutes)} мин назад`, color: "#fcd34d", dot: "#f59e0b", isOnline: false };
    const hours = minutes / 60;
    if (hours < 24) return { label: `Был(а) ${Math.floor(hours)} ч назад`, color: "rgba(255,255,255,0.45)", dot: "#94a3b8", isOnline: false };
    return { label: "Был(а) давно", color: "rgba(255,255,255,0.3)", dot: "#6b7280", isOnline: false };
}

function getPhotoUrl(user: MatchUser): string {
    if (user.photos && user.photos.length > 0) {
        const p = user.photos[0];
        return p.startsWith("http") ? p : `${BackEnd_URL}${p}`;
    }
    if (user.photo) {
        return `${BackEnd_URL}/api/v1/users/${user.telegram_id}/photo`;
    }
    return "/placeholder.svg";
}

export default function MatchesPage({ params }: { params: { users: string } }) {
    const [matches, setMatches] = useState<MatchUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [imgErrors, setImgErrors] = useState<Record<number, boolean>>({});
    const router = useRouter();
    const userId = params.users;
    const fetchingRef = useRef(false);

    const fetchMatches = useCallback(async () => {
        if (fetchingRef.current) return;
        fetchingRef.current = true;
        setLoading(true);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/likes/matches/${userId}`, { cache: "no-store" });
            const data = res.ok ? await res.json() : { items: [] };
            setMatches(data.items ?? []);
            setImgErrors({});
        } catch {
            setMatches([]);
        } finally {
            setLoading(false);
            fetchingRef.current = false;
        }
    }, [userId]);

    // Первая загрузка
    useEffect(() => {
        fetchMatches();
    }, [fetchMatches]);

    // Перезагрузка при возврате через history.back() (popstate) или pageshow
    useEffect(() => {
        const onPop = () => fetchMatches();
        const onShow = (e: PageTransitionEvent) => { if (e.persisted) fetchMatches(); };
        window.addEventListener("popstate", onPop);
        window.addEventListener("pageshow", onShow as EventListener);
        return () => {
            window.removeEventListener("popstate", onPop);
            window.removeEventListener("pageshow", onShow as EventListener);
        };
    }, [fetchMatches]);

    // Пинг: обновляем last_seen
    useEffect(() => {
        const ping = () => fetch(`${BackEnd_URL}/api/v1/users/${userId}/ping`, { method: "POST" }).catch(() => {});
        ping();
        const interval = setInterval(ping, 60_000);
        return () => clearInterval(interval);
    }, [userId]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen" style={{ background: "#0f0f1a" }}>
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-screen pb-20" style={{ background: "#0f0f1a", color: "#fff" }}>
            {/* Header */}
            <div className="px-4 pt-4 pb-2 flex items-center justify-between">
                <div>
                    <h1 className="text-lg font-bold">💌 Матчи</h1>
                    <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>
                        {matches.length > 0 ? `${matches.length} взаимных симпатий` : "Взаимные симпатии"}
                    </p>
                </div>
                <button
                    onClick={fetchMatches}
                    className="w-8 h-8 rounded-full flex items-center justify-center transition-all active:scale-90"
                    style={{ background: "rgba(255,255,255,0.08)" }}
                    title="Обновить"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="23 4 23 10 17 10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                </button>
            </div>

            {matches.length === 0 ? (
                <div className="flex flex-col items-center justify-center flex-1 gap-4 px-8 text-center pt-20">
                    <div className="text-6xl">🤍</div>
                    <h2 className="text-lg font-semibold">Пока нет матчей</h2>
                    <p className="text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>
                        Свайпай анкеты — когда кто-то лайкнет тебя в ответ, появится матч!
                    </p>
                    <button
                        onClick={() => router.push(`/users/${userId}`)}
                        className="mt-4 px-6 py-3 rounded-2xl font-semibold text-white transition-all active:scale-95"
                        style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)" }}
                    >
                        ❤️ Смотреть анкеты
                    </button>
                    <button
                        onClick={fetchMatches}
                        className="px-6 py-2 rounded-2xl text-sm font-medium text-white/60 transition-all active:scale-95"
                        style={{ background: "rgba(255,255,255,0.06)" }}
                    >
                        🔄 Обновить
                    </button>
                </div>
            ) : (
                <div className="flex flex-col gap-2 px-3 pb-2">
                    {matches.map((user) => {
                        const st = getOnlineStatus(user.last_seen);
                        const photoUrl = imgErrors[user.telegram_id] ? "/placeholder.svg" : getPhotoUrl(user);

                        return (
                            <div
                                key={user.telegram_id}
                                className="flex items-center gap-3 rounded-2xl px-3 py-2.5"
                                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}
                            >
                                {/* Avatar */}
                                <button
                                    className="flex-shrink-0"
                                    onClick={() => router.push(`/users/${userId}/view-profile/${user.telegram_id}`)}
                                >
                                    <div className="relative">
                                        <img
                                            src={photoUrl}
                                            alt={user.name}
                                            className="w-12 h-12 rounded-full object-cover"
                                            style={{ border: `2px solid ${st.isOnline ? "#22c55e" : "rgba(236,72,153,0.5)"}` }}
                                            onError={() => {
                                                setImgErrors(prev => ({ ...prev, [user.telegram_id]: true }));
                                            }}
                                        />
                                        <div
                                            className="absolute bottom-0 right-0 w-3 h-3 rounded-full"
                                            style={{ background: st.dot, border: "2px solid #0f0f1a" }}
                                        />
                                    </div>
                                </button>

                                {/* Info */}
                                <button
                                    className="flex-1 min-w-0 text-left"
                                    onClick={() => router.push(`/users/${userId}/view-profile/${user.telegram_id}`)}
                                >
                                    <p className="font-semibold text-sm truncate leading-tight">
                                        {user.name}{user.age ? `, ${user.age}` : ""}
                                    </p>
                                    <p className="text-xs truncate leading-tight" style={{ color: st.color }}>
                                        {st.label}
                                    </p>
                                    {user.city && (
                                        <p className="text-xs truncate leading-tight" style={{ color: "rgba(255,255,255,0.35)" }}>
                                            📍 {user.city}
                                        </p>
                                    )}
                                </button>

                                {/* Action buttons */}
                                <div className="flex flex-col gap-1.5 flex-shrink-0">
                                    <button
                                        onClick={() => router.push(`/users/${userId}/view-profile/${user.telegram_id}`)}
                                        className="px-3 py-1.5 rounded-xl text-xs font-semibold transition-all active:scale-95 whitespace-nowrap"
                                        style={{ background: "rgba(139,92,246,0.25)", color: "#c4b5fd", border: "1px solid rgba(139,92,246,0.3)" }}
                                    >
                                        👤 Профиль
                                    </button>
                                    {user.username ? (
                                        <a
                                            href={`https://t.me/${user.username}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="px-3 py-1.5 rounded-xl text-xs font-semibold text-center transition-all active:scale-95 whitespace-nowrap"
                                            style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)", color: "#fff" }}
                                        >
                                            ✉️ Написать
                                        </a>
                                    ) : (
                                        <div
                                            className="px-3 py-1.5 rounded-xl text-xs font-semibold text-center whitespace-nowrap"
                                            style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.25)" }}
                                        >
                                            Нет @
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            <BottomNav userId={userId} />
        </div>
    );
}
