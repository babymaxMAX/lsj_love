"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BackEnd_URL } from "@/config/url";
import { BottomNav } from "@/components/bottom-nav";

const GENDER_RU: Record<string, string> = {
    Man: "Мужской",
    Female: "Женский",
    Мужской: "Мужской",
    Женский: "Женский",
};

const LOOKING_RU: Record<string, string> = {
    Man: "Мужчину",
    Female: "Девушку",
    Мужской: "Мужчину",
    Женский: "Девушку",
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
    photos: string[];
    is_active: boolean;
}

const MAX_PHOTOS = 6;

export default function ProfilePage({ params }: { params: { users: string } }) {
    const userId = params.users;
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [photos, setPhotos] = useState<string[]>([]);
    const [uploading, setUploading] = useState(false);
    const [deleteIdx, setDeleteIdx] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileRef = useRef<HTMLInputElement>(null);

    const loadUser = useCallback(() => {
        setLoading(true);
        fetch(`${BackEnd_URL}/api/v1/users/${userId}`)
            .then((r) => r.json())
            .then((data: UserProfile) => {
                setUser(data);
                // Строим список фото для отображения
                const photoList: string[] = [];
                if (data.photos?.length) {
                    data.photos.forEach((p) => {
                        photoList.push(p.startsWith("http") ? p : `${BackEnd_URL}${p}`);
                    });
                } else if (data.photo) {
                    photoList.push(`${BackEnd_URL}/api/v1/users/${userId}/photo`);
                }
                setPhotos(photoList);
            })
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, [userId]);

    useEffect(() => { loadUser(); }, [loadUser]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async () => {
            const result = reader.result as string;
            const base64 = result.split(",")[1] ?? "";
            await uploadPhoto(base64);
        };
        reader.readAsDataURL(file);
        e.target.value = "";
    };

    const uploadPhoto = async (base64: string) => {
        setUploading(true);
        setError(null);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/users/${userId}/photos`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image_base64: base64 }),
            });
            const data = await res.json();
            if (!res.ok) {
                setError(data?.error || data?.detail?.error || "Ошибка загрузки");
                return;
            }
            // Обновляем фото из ответа
            const newPhotos = (data.photos as string[]).map((p) =>
                p.startsWith("http") ? p : `${BackEnd_URL}${p}`
            );
            setPhotos(newPhotos);
        } catch {
            setError("Ошибка соединения");
        } finally {
            setUploading(false);
        }
    };

    const deletePhoto = async (index: number) => {
        setDeleteIdx(index);
        setError(null);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/users/${userId}/photos/${index}`, {
                method: "DELETE",
            });
            const data = await res.json();
            if (!res.ok) {
                setError(data?.error || "Ошибка удаления");
                return;
            }
            const newPhotos = (data.photos as string[]).map((p) =>
                p.startsWith("http") ? p : `${BackEnd_URL}${p}`
            );
            setPhotos(newPhotos);
        } catch {
            setError("Ошибка соединения");
        } finally {
            setDeleteIdx(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen" style={{ background: "#0f0f1a" }}>
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-4 text-center px-8" style={{ background: "#0f0f1a" }}>
                <div className="text-5xl">😕</div>
                <p className="text-white/50">Профиль не найден</p>
            </div>
        );
    }

    const slots = Array.from({ length: MAX_PHOTOS });

    return (
        <div className="flex flex-col min-h-screen pb-24" style={{ background: "#0f0f1a", color: "#fff" }}>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFileSelect} />

            {/* Header */}
            <div className="px-4 py-5 flex items-center gap-3">
                <div>
                    <h1 className="text-xl font-bold">Мой профиль</h1>
                    <p className="text-xs text-white/40 mt-0.5">До {MAX_PHOTOS} фотографий</p>
                </div>
            </div>

            {/* Photo gallery grid */}
            <div className="px-4">
                <div className="grid grid-cols-3 gap-2">
                    {slots.map((_, i) => {
                        const hasPhoto = i < photos.length;
                        const isMain = i === 0;
                        const isDeleting = deleteIdx === i;

                        return (
                            <div
                                key={i}
                                className="relative rounded-xl overflow-hidden"
                                style={{
                                    aspectRatio: "1",
                                    background: hasPhoto ? undefined : "rgba(255,255,255,0.05)",
                                    border: !hasPhoto ? "1.5px dashed rgba(255,255,255,0.15)" : undefined,
                                }}
                            >
                                {hasPhoto ? (
                                    <>
                                        <img
                                            src={photos[i]}
                                            alt={`Фото ${i + 1}`}
                                            className="w-full h-full object-cover"
                                            onError={(e) => {
                                                const img = e.target as HTMLImageElement;
                                                if (!img.src.endsWith("/placeholder.svg")) img.src = "/placeholder.svg";
                                            }}
                                        />
                                        {isMain && (
                                            <div
                                                className="absolute top-1.5 left-1.5 text-xs px-1.5 py-0.5 rounded-full font-semibold"
                                                style={{ background: "rgba(124,58,237,0.9)", fontSize: 9 }}
                                            >
                                                ГЛАВНОЕ
                                            </div>
                                        )}
                                        <button
                                            onClick={() => deletePhoto(i)}
                                            disabled={isDeleting}
                                            className="absolute top-1.5 right-1.5 w-6 h-6 rounded-full flex items-center justify-center transition-all active:scale-90"
                                            style={{ background: "rgba(0,0,0,0.6)" }}
                                        >
                                            {isDeleting ? (
                                                <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                                            ) : (
                                                <span style={{ fontSize: 11, lineHeight: 1, color: "#fff" }}>✕</span>
                                            )}
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        onClick={() => !uploading && photos.length < MAX_PHOTOS && fileRef.current?.click()}
                                        disabled={uploading || photos.length >= MAX_PHOTOS}
                                        className="w-full h-full flex flex-col items-center justify-center gap-1 transition-all active:scale-95"
                                    >
                                        {uploading && i === photos.length ? (
                                            <div className="w-5 h-5 border border-purple-400 border-t-transparent rounded-full animate-spin" />
                                        ) : (
                                            <>
                                                <span className="text-2xl text-white/20">+</span>
                                                <span className="text-xs text-white/20">Фото</span>
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Add button if has space and no empty slot visible */}
                {photos.length < MAX_PHOTOS && photos.length === MAX_PHOTOS && (
                    <button
                        onClick={() => !uploading && fileRef.current?.click()}
                        disabled={uploading}
                        className="mt-3 w-full py-3 rounded-2xl text-sm font-medium text-white/70 transition-all active:scale-95"
                        style={{ background: "rgba(255,255,255,0.06)" }}
                    >
                        {uploading ? "Загружаю..." : "+ Добавить фото"}
                    </button>
                )}

                {error && (
                    <p className="mt-2 text-xs text-red-400 text-center">{error}</p>
                )}

                <p className="mt-2 text-xs text-white/30 text-center">
                    Нажми «+» чтобы добавить фото · ✕ чтобы удалить
                </p>
            </div>

            {/* User info */}
            <div className="px-4 mt-5 space-y-3">
                <div
                    className="rounded-2xl p-4 space-y-3"
                    style={{ background: "rgba(255,255,255,0.06)" }}
                >
                    <div className="flex items-center gap-3">
                        <span className="text-lg">👤</span>
                        <div>
                            <p className="text-xs text-white/40">Имя</p>
                            <p className="text-sm font-medium">{user.name}{user.age ? `, ${user.age}` : ""}</p>
                        </div>
                    </div>
                    {user.city && (
                        <div className="flex items-center gap-3">
                            <span className="text-lg">📍</span>
                            <div>
                                <p className="text-xs text-white/40">Город</p>
                                <p className="text-sm font-medium">{user.city}</p>
                            </div>
                        </div>
                    )}
                    {user.gender && (
                        <div className="flex items-center gap-3">
                            <span className="text-lg">👫</span>
                            <div>
                                <p className="text-xs text-white/40">Пол</p>
                                <p className="text-sm font-medium">{GENDER_RU[user.gender] ?? user.gender}</p>
                            </div>
                        </div>
                    )}
                    {user.looking_for && (
                        <div className="flex items-center gap-3">
                            <span className="text-lg">🔍</span>
                            <div>
                                <p className="text-xs text-white/40">Ищу</p>
                                <p className="text-sm font-medium">{LOOKING_RU[user.looking_for] ?? user.looking_for}</p>
                            </div>
                        </div>
                    )}
                    {user.username && (
                        <div className="flex items-center gap-3">
                            <span className="text-lg">📎</span>
                            <div>
                                <p className="text-xs text-white/40">Username</p>
                                <p className="text-sm font-medium">@{user.username}</p>
                            </div>
                        </div>
                    )}
                    {user.about && (
                        <div className="pt-2 border-t border-white/10">
                            <p className="text-xs text-white/40 mb-1">✍️ О себе</p>
                            <p className="text-sm text-white/80 leading-relaxed">{user.about}</p>
                        </div>
                    )}
                </div>

                <div
                    className="rounded-2xl p-4"
                    style={{ background: "rgba(255,255,255,0.04)" }}
                >
                    <p className="text-sm text-white/40 text-center">
                        Для редактирования имени, города и описания — используй кнопку ⚙️ в боте
                    </p>
                </div>
            </div>

            <BottomNav userId={userId} />
        </div>
    );
}
