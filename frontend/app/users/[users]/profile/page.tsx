"use client";
import { useEffect, useState } from "react";
import { BackEnd_URL } from "@/config/url";
import { BottomNav } from "@/components/bottom-nav";

const GENDER_RU: Record<string, string> = {
    Man: "Мужской",
    Female: "Женский",
};

const LOOKING_RU: Record<string, string> = {
    Man: "Мужчину",
    Female: "Девушку",
};

interface UserProfile {
    telegram_id: number;
    name: string;
    username?: string;
    age: number;
    city: string;
    gender: string;
    looking_for: string;
    about?: string;
    photo?: string;
    is_active: boolean;
}

export default function ProfilePage({ params }: { params: { users: string } }) {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/users/${params.users}`)
            .then((r) => r.json())
            .then(setUser)
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, [params.users]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-4xl animate-pulse">👤</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-4 text-center px-8">
                <div className="text-5xl">😕</div>
                <p className="text-default-500">Профиль не найден</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-screen pb-20">
            {/* Шапка */}
            <div className="px-4 py-4 border-b border-divider">
                <h1 className="text-xl font-bold">👤 Мой профиль</h1>
            </div>

            {/* Фото */}
            <div className="relative">
                {user.photo ? (
                    <img
                        src={user.photo}
                        alt={user.name}
                        className="w-full h-72 object-cover"
                    />
                ) : (
                    <div className="w-full h-72 bg-content2 flex items-center justify-center">
                        <span className="text-6xl">📷</span>
                    </div>
                )}
                <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-black/70 to-transparent" />
                <div className="absolute bottom-4 left-4 text-white">
                    <h2 className="text-2xl font-bold">{user.name}, {user.age}</h2>
                    <p className="text-sm opacity-80">📍 {user.city}</p>
                </div>
            </div>

            {/* Данные */}
            <div className="p-4 flex flex-col gap-3">
                <div className="bg-content1 rounded-2xl p-4 flex flex-col gap-3">
                    <InfoRow icon="👫" label="Пол" value={GENDER_RU[user.gender] ?? user.gender} />
                    <InfoRow icon="🔍" label="Ищу" value={LOOKING_RU[user.looking_for] ?? user.looking_for} />
                    {user.username && (
                        <InfoRow icon="📎" label="Username" value={`@${user.username}`} />
                    )}
                    {user.about && (
                        <div className="pt-2 border-t border-divider">
                            <p className="text-xs text-default-400 mb-1">✍️ О себе</p>
                            <p className="text-sm">{user.about}</p>
                        </div>
                    )}
                </div>

                {/* Кнопка редактирования */}
                <div className="bg-content1 rounded-2xl p-4">
                    <p className="text-sm text-default-400 text-center">
                        Для редактирования профиля используй кнопку ⚙️ в боте
                    </p>
                </div>
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}

function InfoRow({ icon, label, value }: { icon: string; label: string; value: string }) {
    return (
        <div className="flex items-center gap-3">
            <span className="text-xl w-8 text-center">{icon}</span>
            <div>
                <p className="text-xs text-default-400">{label}</p>
                <p className="text-sm font-medium">{value}</p>
            </div>
        </div>
    );
}
