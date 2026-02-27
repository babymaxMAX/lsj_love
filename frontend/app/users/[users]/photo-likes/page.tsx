"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";
import { BottomNav } from "@/components/bottom-nav";

interface Liker {
    telegram_id: number;
    name: string;
    photo_url: string;
}

interface PhotoData {
    photo_index: number;
    photo_url: string;
    total_likes: number;
    recent_likers: Liker[];
}

function formatTimeAgo(dateStr: string): string {
    if (!dateStr) return "";
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "только что";
    if (mins < 60) return `${mins} мин назад`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs} ч назад`;
    const days = Math.floor(hrs / 24);
    return `${days} д назад`;
}

export default function PhotoLikesPage() {
    const params = useParams();
    const router = useRouter();
    const userId = params.users as string;

    const [photos, setPhotos] = useState<PhotoData[]>([]);
    const [totalAll, setTotalAll] = useState(0);
    const [isPremium, setIsPremium] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/photo-interactions/my-likes/${userId}`)
            .then((r) => r.json())
            .then((d) => {
                setPhotos(d.photos || []);
                setTotalAll(d.total_all_photos || 0);
                setIsPremium(d.is_premium || false);
            })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [userId]);

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
            <div
                className="flex items-center gap-3 px-4 py-3"
                style={{
                    background: "rgba(15,15,26,0.97)",
                    backdropFilter: "blur(12px)",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    paddingTop: "calc(env(safe-area-inset-top, 0px) + 12px)",
                }}
            >
                <button
                    onClick={() => router.back()}
                    style={{
                        width: 36, height: 36, borderRadius: 12,
                        background: "rgba(255,255,255,0.08)",
                        border: "none", color: "#fff", fontSize: 18, cursor: "pointer",
                        display: "flex", alignItems: "center", justifyContent: "center",
                    }}
                >
                    ←
                </button>
                <div>
                    <h1 className="text-lg font-bold">❤️ Лайки на фото</h1>
                    <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
                        Всего: {totalAll} лайков
                    </p>
                </div>
            </div>

            <div className="px-4 py-4 flex flex-col gap-4">
                {photos.length === 0 && (
                    <div className="text-center py-12">
                        <div className="text-5xl mb-4">📷</div>
                        <p style={{ color: "rgba(255,255,255,0.5)" }}>Добавь фото в профиль чтобы получать лайки</p>
                    </div>
                )}

                {photos.map((photo) => (
                    <div
                        key={photo.photo_index}
                        style={{
                            background: "rgba(255,255,255,0.05)",
                            borderRadius: 20,
                            overflow: "hidden",
                            border: "1px solid rgba(255,255,255,0.08)",
                        }}
                    >
                        {/* Photo + like count badge */}
                        <div style={{ position: "relative" }}>
                            <img
                                src={`${BackEnd_URL}${photo.photo_url}`}
                                alt={`Фото ${photo.photo_index + 1}`}
                                style={{ width: "100%", height: 200, objectFit: "cover", objectPosition: "top" }}
                                onError={(e) => {
                                    (e.target as HTMLImageElement).src = "/placeholder.svg";
                                }}
                            />
                            <div
                                style={{
                                    position: "absolute", bottom: 10, right: 10,
                                    background: "rgba(0,0,0,0.6)", borderRadius: 100,
                                    padding: "4px 12px", color: "#fff", fontSize: 14, fontWeight: 700,
                                    backdropFilter: "blur(6px)",
                                }}
                            >
                                ❤️ {photo.total_likes}
                            </div>
                        </div>

                        {isPremium ? (
                            <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
                                {photo.recent_likers.length > 0 ? (
                                    photo.recent_likers.map((liker) => (
                                        <div
                                            key={liker.telegram_id}
                                            style={{ display: "flex", alignItems: "center", gap: 12 }}
                                        >
                                            <img
                                                src={liker.photo_url ? `${BackEnd_URL}${liker.photo_url}` : "/placeholder.svg"}
                                                alt={liker.name}
                                                style={{
                                                    width: 44, height: 44, borderRadius: "50%",
                                                    objectFit: "cover",
                                                }}
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).src = "/placeholder.svg";
                                                }}
                                            />
                                            <div style={{ flex: 1 }}>
                                                <div style={{ fontWeight: 600, fontSize: 15 }}>{liker.name}</div>
                                            </div>
                                            <button
                                                onClick={() => router.push(`/users/${userId}/view-profile/${liker.telegram_id}`)}
                                                style={{
                                                    padding: "8px 16px", borderRadius: 100,
                                                    background: "linear-gradient(135deg, #7c3aed, #db2777)",
                                                    color: "#fff", border: "none", fontSize: 13, fontWeight: 600,
                                                    cursor: "pointer",
                                                }}
                                            >
                                                Смотреть
                                            </button>
                                        </div>
                                    ))
                                ) : (
                                    <div style={{ color: "#666", fontSize: 14, padding: "8px 0" }}>
                                        Пока нет лайков на это фото
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div style={{ padding: 16, textAlign: "center" }}>
                                <div style={{ fontSize: 32, marginBottom: 8 }}>🔒</div>
                                <div style={{ fontWeight: 700, marginBottom: 4 }}>
                                    {photo.total_likes} человек лайкнули это фото
                                </div>
                                <div style={{ color: "#888", fontSize: 13, marginBottom: 12 }}>
                                    Оформи Premium чтобы увидеть кто
                                </div>
                                <button
                                    onClick={() => router.push(`/users/${userId}/premium`)}
                                    style={{
                                        padding: "10px 24px", borderRadius: 100,
                                        background: "linear-gradient(135deg, #f59e0b, #ef4444)",
                                        color: "#fff", border: "none", fontWeight: 700,
                                        cursor: "pointer",
                                    }}
                                >
                                    ⭐ Получить Premium
                                </button>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <BottomNav userId={userId} />
        </div>
    );
}
