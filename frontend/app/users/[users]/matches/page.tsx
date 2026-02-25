"use client";
import { useEffect, useState } from "react";
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

/** Возвращает { label, color } для статуса онлайн */
function getOnlineStatus(lastSeen?: string): { label: string; color: string } {
    if (!lastSeen) return { label: "Не в сети", color: "#6b7280" };
    const diff = Date.now() - new Date(lastSeen).getTime();
    const minutes = diff / 60000;
    if (minutes < 5) return { label: "Онлайн", color: "#22c55e" };
    if (minutes < 60) return { label: `Был(а) ${Math.floor(minutes)} мин назад`, color: "#f59e0b" };
    const hours = minutes / 60;
    if (hours < 24) return { label: `Был(а) ${Math.floor(hours)} ч назад`, color: "#94a3b8" };
    return { label: "Был(а) давно", color: "#6b7280" };
}

export default function MatchesPage({ params }: { params: { users: string } }) {
    const [matches, setMatches] = useState<MatchUser[]>([]);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const userId = params.users;

    useEffect(() => {
        const fetchMatches = async () => {
            try {
                const res = await fetch(`${BackEnd_URL}/api/v1/likes/matches/${userId}`);
                const data = res.ok ? await res.json() : { items: [] };
                setMatches(data.items ?? []);
            } catch {
                setMatches([]);
            } finally {
                setLoading(false);
            }
        };
        fetchMatches();
    }, [userId]);

    // Пинг: обновляем last_seen
    useEffect(() => {
        const ping = () => fetch(`${BackEnd_URL}/api/v1/users/${userId}/ping`, { method: "POST" }).catch(() => {});
        ping();
        const interval = setInterval(ping, 60_000);
        return () => clearInterval(interval);
    }, [userId]);

    const getPhotoUrl = (user: MatchUser) => {
        if (user.photos && user.photos.length > 0) {
            const p = user.photos[0];
            return p.startsWith("http") ? p : `${BackEnd_URL}${p}`;
        }
        if (user.photo) {
            return `${BackEnd_URL}/api/v1/users/${user.telegram_id}/photo`;
        }
        return "/placeholder.svg";
    };

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
            <div className="px-4 pt-4 pb-2">
                <h1 className="text-lg font-bold">💌 Матчи</h1>
                <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>
                    {matches.length > 0 ? `${matches.length} взаимных симпатий` : "Взаимные симпатии"}
                </p>
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
                </div>
            ) : (
                <div className="flex flex-col gap-2 px-3 pb-2">
                    {matches.map((user) => (
                        <div
                            key={user.telegram_id}
                            className="flex items-center gap-3 rounded-2xl px-3 py-2.5"
                            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}
                        >
                            {/* Avatar — кликабельна */}
                            <button
                                className="flex-shrink-0"
                                onClick={() => router.push(`/users/${userId}/view-profile/${user.telegram_id}`)}
                            >
                                {(() => {
                                    const status = getOnlineStatus(user.last_seen);
                                    const isOnline = status.color === "#22c55e";
                                    return (
                                        <div className="relative">
                                            <img
                                                src={getPhotoUrl(user)}
                                                alt={user.name}
                                                className="w-12 h-12 rounded-full object-cover"
                                                style={{ border: `2px solid ${isOnline ? "#22c55e" : "rgba(236,72,153,0.5)"}` }}
                                                onError={(e) => {
                                                    const el = e.target as HTMLImageElement;
                                                    if (!el.src.endsWith("/placeholder.svg")) el.src = "/placeholder.svg";
                                                }}
                                            />
                                            <div
                                                className="absolute bottom-0 right-0 w-3 h-3 rounded-full"
                                                style={{ background: status.color, border: "2px solid #0f0f1a" }}
                                            />
                                        </div>
                                    );
                                })()}
                            </button>

                            {/* Info */}
                            <button
                                className="flex-1 min-w-0 text-left"
                                onClick={() => router.push(`/users/${userId}/view-profile/${user.telegram_id}`)}
                            >
                                <p className="font-semibold text-sm truncate leading-tight">
                                    {user.name}{user.age ? `, ${user.age}` : ""}
                                </p>
                                <p className="text-xs truncate leading-tight" style={{ color: getOnlineStatus(user.last_seen).color }}>
                                    {getOnlineStatus(user.last_seen).label}
                                </p>
                                {user.city && (
                                    <p className="text-xs truncate leading-tight" style={{ color: "rgba(255,255,255,0.35)" }}>
                                        📍 {user.city}
                                    </p>
                                )}
                            </button>

                            {/* Action buttons — вертикально справа */}
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
                    ))}
                </div>
            )}

            <BottomNav userId={userId} />
        </div>
    );
}
