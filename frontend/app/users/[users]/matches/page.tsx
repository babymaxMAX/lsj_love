"use client";
import { useEffect, useState } from "react";
import { BackEnd_URL } from "@/config/url";
import { BottomNav } from "@/components/bottom-nav";

interface MatchUser {
    telegram_id: number;
    name: string;
    age: number;
    city: string;
    photo: string;
    username?: string;
    about?: string;
}

export default function MatchesPage({ params }: { params: { users: string } }) {
    const [matches, setMatches] = useState<MatchUser[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Получаем тех, кто лайкнул нас И кого мы лайкнули (взаимные)
        const fetchMatches = async () => {
            try {
                const [byRes, fromRes] = await Promise.all([
                    fetch(`${BackEnd_URL}/api/v1/users/by/${params.users}`),
                    fetch(`${BackEnd_URL}/api/v1/users/from/${params.users}`),
                ]);
                const byData = byRes.ok ? await byRes.json() : { items: [] };
                const fromData = fromRes.ok ? await fromRes.json() : { items: [] };

                // Взаимные = те, кто лайкнул нас И кого мы лайкнули
                const likedByIds = new Set(byData.items.map((u: MatchUser) => u.telegram_id));
                const mutual = fromData.items.filter((u: MatchUser) => likedByIds.has(u.telegram_id));
                setMatches(mutual);
            } catch {
                setMatches([]);
            } finally {
                setLoading(false);
            }
        };
        fetchMatches();
    }, [params.users]);

    return (
        <div className="flex flex-col min-h-screen pb-20">
            <div className="px-4 py-4 border-b border-divider">
                <h1 className="text-xl font-bold">💌 Матчи</h1>
                <p className="text-sm text-default-400 mt-1">Взаимные симпатии</p>
            </div>

            {loading ? (
                <div className="flex items-center justify-center flex-1">
                    <div className="text-4xl animate-pulse">💌</div>
                </div>
            ) : matches.length === 0 ? (
                <div className="flex flex-col items-center justify-center flex-1 gap-4 px-8 text-center">
                    <div className="text-6xl">🤍</div>
                    <h2 className="text-lg font-semibold">Пока нет матчей</h2>
                    <p className="text-default-400 text-sm">
                        Свайпай анкеты, и когда кто-то лайкнет тебя в ответ — появится матч!
                    </p>
                </div>
            ) : (
                <div className="flex flex-col gap-3 p-4">
                    {matches.map((user) => (
                        <div
                            key={user.telegram_id}
                            className="flex items-center gap-4 bg-content1 rounded-2xl p-3 shadow-sm"
                        >
                            <img
                                src={user.photo || "/placeholder.jpg"}
                                alt={user.name}
                                className="w-16 h-16 rounded-full object-cover flex-shrink-0"
                            />
                            <div className="flex-1 min-w-0">
                                <p className="font-semibold truncate">{user.name}, {user.age}</p>
                                <p className="text-sm text-default-400 truncate">📍 {user.city}</p>
                                {user.about && (
                                    <p className="text-xs text-default-500 truncate mt-1">{user.about}</p>
                                )}
                            </div>
                            {user.username && (
                                <a
                                    href={`https://t.me/${user.username}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex-shrink-0 bg-primary text-white text-xs font-medium px-3 py-2 rounded-xl"
                                >
                                    Написать
                                </a>
                            )}
                        </div>
                    ))}
                </div>
            )}

            <BottomNav userId={params.users} />
        </div>
    );
}
