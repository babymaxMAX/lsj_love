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
        <div className="flex flex-col min-h-screen pb-24" style={{ background: "#0f0f1a", color: "#fff" }}>
            {/* Header */}
            <div className="px-4 pt-5 pb-3">
                <h1 className="text-xl font-bold">💌 Матчи</h1>
                <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.4)" }}>
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
                <div className="flex flex-col gap-3 px-4">
                    {matches.map((user) => (
                        <div
                            key={user.telegram_id}
                            className="rounded-2xl overflow-hidden"
                            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}
                        >
                            {/* Clickable top section → view profile */}
                            <button
                                className="w-full flex items-center gap-4 p-4 text-left transition-all active:opacity-80"
                                onClick={() => router.push(`/users/${userId}/view-profile/${user.telegram_id}`)}
                            >
                                <div className="relative flex-shrink-0">
                                    <img
                                        src={getPhotoUrl(user)}
                                        alt={user.name}
                                        className="w-16 h-16 rounded-full object-cover"
                                        style={{ border: "2px solid rgba(236,72,153,0.5)" }}
                                        onError={(e) => {
                                            const el = e.target as HTMLImageElement;
                                            if (!el.src.endsWith("/placeholder.svg")) el.src = "/placeholder.svg";
                                        }}
                                    />
                                    {/* Online dot */}
                                    <div
                                        className="absolute bottom-0 right-0 w-4 h-4 rounded-full"
                                        style={{ background: "#22c55e", border: "2px solid #0f0f1a" }}
                                    />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-bold text-base truncate">
                                        {user.name}{user.age ? `, ${user.age}` : ""}
                                    </p>
                                    <p className="text-sm truncate" style={{ color: "rgba(255,255,255,0.5)" }}>
                                        📍 {user.city}
                                    </p>
                                    {user.about && (
                                        <p className="text-xs truncate mt-0.5" style={{ color: "rgba(255,255,255,0.35)" }}>
                                            {user.about}
                                        </p>
                                    )}
                                </div>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="2">
                                    <path d="M9 18l6-6-6-6" />
                                </svg>
                            </button>

                            {/* Action buttons */}
                            <div className="flex gap-2 px-4 pb-4">
                                <button
                                    onClick={() => router.push(`/users/${userId}/view-profile/${user.telegram_id}`)}
                                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all active:scale-95"
                                    style={{ background: "rgba(139,92,246,0.2)", color: "#a78bfa", border: "1px solid rgba(139,92,246,0.3)" }}
                                >
                                    👤 Профиль
                                </button>
                                {user.username ? (
                                    <a
                                        href={`https://t.me/${user.username}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-center transition-all active:scale-95"
                                        style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)", color: "#fff" }}
                                    >
                                        ✉️ Написать
                                    </a>
                                ) : (
                                    <div
                                        className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-center"
                                        style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.3)" }}
                                    >
                                        Нет username
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
