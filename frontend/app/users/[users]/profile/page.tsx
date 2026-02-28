"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";
import { BottomNav } from "@/components/bottom-nav";
import { ProfileAnswers } from "@/components/profile-answers";

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
    media_types: string[];
    is_active: boolean;
    referral_balance?: number;
    premium_type?: string | null;
}

const MAX_MEDIA = 6;

function isVideoUrl(url: string, mediaType?: string) {
    if (mediaType === "video") return true;
    return /\.(mp4|mov|webm|avi)(\?|$)/i.test(url);
}

export default function ProfilePage({ params }: { params: { users: string } }) {
    const userId = params.users;
    const router = useRouter();
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [mediaUrls, setMediaUrls] = useState<string[]>([]);
    const [mediaTypes, setMediaTypes] = useState<string[]>([]);
    const [sliderIdx, setSliderIdx] = useState(0);
    const [editOpen, setEditOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [pendingSlot, setPendingSlot] = useState<number | null>(null);
    const [deleteIdx, setDeleteIdx] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [photoLikes, setPhotoLikes] = useState<Record<number, number>>({});
    const [refCopied, setRefCopied] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);
    const sliderRef = useRef<HTMLDivElement>(null);
    const touchStartX = useRef<number | null>(null);

    // Расширяем Mini App на весь экран
    useEffect(() => {
        if (typeof window !== "undefined" && window.Telegram?.WebApp) {
            window.Telegram.WebApp.expand();
            window.Telegram.WebApp.ready();
        }
    }, []);

    const loadUser = useCallback(() => {
        setLoading(true);
        fetch(`${BackEnd_URL}/api/v1/users/${userId}`)
            .then((r) => r.json())
            .then((data: UserProfile) => {
                setUser(data);
                const t = Date.now();
                const urls = (data.photos ?? []).map((p) => {
                    const base = p.startsWith("http") ? p : `${BackEnd_URL}${p}`;
                    // cache-bust только для изображений
                    if (/\.(mp4|mov|webm|avi)(\?|$)/i.test(base)) return base;
                    const sep = base.includes("?") ? "&" : "?";
                    return `${base}${sep}t=${t}`;
                });
                const types = data.media_types ?? urls.map(() => "image");
                setMediaUrls(urls);
                setMediaTypes(types);
                setSliderIdx(0);
            })
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, [userId]);

    useEffect(() => { loadUser(); }, [loadUser]);

    // Загружаем лайки для каждого фото
    useEffect(() => {
        if (!mediaUrls.length) return;
        mediaUrls.forEach((_, i) => {
            fetch(`${BackEnd_URL}/api/v1/photo-interactions/likes/${userId}/${i}?viewer_id=${userId}`)
                .then(r => r.ok ? r.json() : null)
                .then(d => d && setPhotoLikes(prev => ({ ...prev, [i]: d.count })))
                .catch(() => {});
        });
    }, [userId, mediaUrls]);

    // ── File picker ────────────────────────────────────────────────────────────
    const openPicker = (slotIndex: number) => {
        setPendingSlot(slotIndex);
        setError(null);
        fileRef.current?.click();
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        e.target.value = "";

        const isVideo = file.type.startsWith("video/");

        if (isVideo) {
            // Видео: проверяем размер (60 МБ максимум) и загружаем через FormData
            if (file.size > 60 * 1024 * 1024) {
                setError("Видео слишком большое (максимум 60 МБ)");
                setPendingSlot(null);
                return;
            }
            uploadMediaMultipart(file);
        } else {
            // Изображения: сжимаем через canvas и загружаем через base64
            if (file.size > 20 * 1024 * 1024) {
                setError("Фото слишком большое (максимум 20 МБ)");
                setPendingSlot(null);
                return;
            }
            const reader = new FileReader();
            reader.onload = () => {
                const result = reader.result as string;
                const img = new Image();
                img.onload = async () => {
                    const canvas = document.createElement("canvas");
                    const MAX = 1280;
                    let w = img.width;
                    let h = img.height;
                    if (w > MAX || h > MAX) {
                        const r = Math.min(MAX / w, MAX / h);
                        w = Math.round(w * r);
                        h = Math.round(h * r);
                    }
                    canvas.width = w;
                    canvas.height = h;
                    canvas.getContext("2d")?.drawImage(img, 0, 0, w, h);
                    const compressed = canvas.toDataURL("image/jpeg", 0.85);
                    const base64 = compressed.split(",")[1] ?? "";
                    await uploadMediaBase64(base64, "image/jpeg");
                };
                img.src = result;
            };
            reader.readAsDataURL(file);
        }
    };

    /** Добавляет cache-bust параметр к URL чтобы браузер не кешировал старое фото */
    const bustCache = (urls: string[]): string[] => {
        const t = Date.now();
        return urls.map((u) => {
            // Для видео не добавляем — может сломать стриминг
            if (/\.(mp4|mov|webm|avi)(\?|$)/i.test(u)) return u;
            const sep = u.includes("?") ? "&" : "?";
            return `${u}${sep}t=${t}`;
        });
    };

    /** Загрузка видео через multipart FormData — без base64 overhead, до 60 МБ */
    const uploadMediaMultipart = async (file: File) => {
        const slot = pendingSlot;
        setPendingSlot(null);
        setUploading(true);
        setError(null);

        const isReplace = slot !== null && slot < mediaUrls.length;
        const formData = new FormData();
        formData.append("file", file);
        if (isReplace && slot !== null) {
            formData.append("replace_index", String(slot));
        }

        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/users/${userId}/photos/upload`, {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            if (!res.ok) {
                const errMsg = data?.detail?.error || data?.error || data?.detail || "Ошибка загрузки видео";
                setError(typeof errMsg === "string" ? errMsg : JSON.stringify(errMsg));
                return;
            }
            const rawUrls = (data.photos as string[]).map((p) =>
                p.startsWith("http") ? p : `${BackEnd_URL}${p}`
            );
            const newUrls = bustCache(rawUrls);
            setMediaUrls(newUrls);
            setMediaTypes(newUrls.map((u) => (/\.(mp4|mov|webm|avi)(\?|$)/i.test(u) ? "video" : "image")));
            setSliderIdx(isReplace && slot !== null ? slot : newUrls.length - 1);
        } catch {
            setError("Ошибка соединения при загрузке видео");
        } finally {
            setUploading(false);
        }
    };

    /** Загрузка изображений через JSON/base64 (со сжатием) */
    const uploadMediaBase64 = async (base64: string, mimeType: string) => {
        const slot = pendingSlot;
        setPendingSlot(null);
        setUploading(true);
        setError(null);

        const isReplace = slot !== null && slot < mediaUrls.length;
        const body: Record<string, unknown> = {
            image_base64: base64,
            media_type: mimeType,
        };
        if (isReplace) body.replace_index = slot;

        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/users/${userId}/photos`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (!res.ok) {
                const errMsg = data?.detail?.error || data?.error || data?.detail || "Ошибка загрузки";
                setError(typeof errMsg === "string" ? errMsg : JSON.stringify(errMsg));
                return;
            }
            const rawUrls = (data.photos as string[]).map((p) =>
                p.startsWith("http") ? p : `${BackEnd_URL}${p}`
            );
            const newUrls = bustCache(rawUrls);
            setMediaUrls(newUrls);
            setMediaTypes(newUrls.map((u) => (/\.(mp4|mov|webm|avi)(\?|$)/i.test(u) ? "video" : "image")));
            setSliderIdx(isReplace && slot !== null ? slot : newUrls.length - 1);
        } catch {
            setError("Ошибка соединения");
        } finally {
            setUploading(false);
        }
    };

    const deleteMedia = async (index: number) => {
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
            const rawUrls = (data.photos as string[]).map((p) =>
                p.startsWith("http") ? p : `${BackEnd_URL}${p}`
            );
            const newUrls = bustCache(rawUrls);
            setMediaUrls(newUrls);
            setMediaTypes(newUrls.map((u) => (/\.(mp4|mov|webm|avi)(\?|$)/i.test(u) ? "video" : "image")));
            if (sliderIdx >= newUrls.length) setSliderIdx(Math.max(0, newUrls.length - 1));
        } catch {
            setError("Ошибка соединения");
        } finally {
            setDeleteIdx(null);
        }
    };

    // ── Slider touch swipe ─────────────────────────────────────────────────────
    const handleTouchStart = (e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
    };
    const handleTouchEnd = (e: React.TouchEvent) => {
        if (touchStartX.current === null) return;
        const dx = e.changedTouches[0].clientX - touchStartX.current;
        if (Math.abs(dx) > 40) {
            if (dx < 0) setSliderIdx((i) => Math.min(i + 1, mediaUrls.length - 1));
            else setSliderIdx((i) => Math.max(i - 1, 0));
        }
        touchStartX.current = null;
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

    const slots = Array.from({ length: MAX_MEDIA });
    const hasMedia = mediaUrls.length > 0;

    const pt = user.premium_type;
    const headerGradient = pt === "vip"
        ? "linear-gradient(135deg, rgba(245,158,11,0.15), rgba(234,179,8,0.08))"
        : pt === "premium"
        ? "linear-gradient(135deg, rgba(239,68,68,0.12), rgba(236,72,153,0.06))"
        : "rgba(15,15,26,0.97)";
    const headerBorder = pt === "vip" ? "1px solid rgba(245,158,11,0.3)"
        : pt === "premium" ? "1px solid rgba(239,68,68,0.2)"
        : "1px solid rgba(255,255,255,0.06)";
    const mediaBorder = pt === "vip" ? "3px solid #f59e0b"
        : pt === "premium" ? "3px solid #ef4444" : "none";

    return (
        <div className="flex flex-col min-h-screen pb-24" style={{ background: "#0f0f1a", color: "#fff" }}>
            <input
                ref={fileRef}
                type="file"
                accept="image/*,video/*"
                className="hidden"
                onChange={handleFileSelect}
            />

            {/* ── Header (sticky) ── */}
            <div
                className="sticky top-0 z-30 flex items-center justify-between px-4 py-3"
                style={{ background: headerGradient, backdropFilter: "blur(12px)", borderBottom: headerBorder }}
            >
                <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <h1 className="text-lg font-bold leading-tight">Мой профиль</h1>
                        {pt === "vip" && (
                            <span style={{ fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 100, background: "linear-gradient(135deg, #f59e0b, #eab308)", color: "#000" }}>VIP</span>
                        )}
                        {pt === "premium" && (
                            <span style={{ fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 100, background: "linear-gradient(135deg, #ef4444, #ec4899)", color: "#fff" }}>PRO</span>
                        )}
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>До {MAX_MEDIA} фото и видео</p>
                </div>
                <button
                    onClick={() => setEditOpen(true)}
                    className="flex items-center gap-1.5 rounded-xl text-sm font-semibold text-white transition-all active:scale-95"
                    style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)", padding: "8px 16px", flexShrink: 0 }}
                >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5" />
                        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                    Изменить
                </button>
            </div>

            {/* ── Media Slider ── */}
            <div
                className="relative mx-4 rounded-3xl overflow-hidden select-none"
                style={{ aspectRatio: "4/5", background: "rgba(255,255,255,0.05)", border: mediaBorder }}
                ref={sliderRef}
                onTouchStart={handleTouchStart}
                onTouchEnd={handleTouchEnd}
            >
                {hasMedia ? (
                    <>
                        {mediaUrls.map((url, i) => (
                            <div
                                key={url}
                                className="absolute inset-0 transition-opacity duration-300"
                                style={{ opacity: i === sliderIdx ? 1 : 0, pointerEvents: i === sliderIdx ? "auto" : "none" }}
                            >
                                {isVideoUrl(url, mediaTypes[i]) ? (
                                    <video
                                        src={url}
                                        className="w-full h-full object-cover"
                                        controls
                                        playsInline
                                        loop
                                    />
                                ) : (
                                    <img
                                        src={url}
                                        alt={`Медиа ${i + 1}`}
                                        className="w-full h-full object-cover"
                                        onError={(e) => {
                                            const el = e.target as HTMLImageElement;
                                            if (!el.src.endsWith("/placeholder.svg")) el.src = "/placeholder.svg";
                                        }}
                                    />
                                )}
                            </div>
                        ))}

                        {/* Gradient overlay bottom */}
                        <div
                            className="absolute inset-x-0 bottom-0 h-24"
                            style={{ background: "linear-gradient(to top, rgba(0,0,0,0.6), transparent)" }}
                        />

                        {/* Slide dots */}
                        {mediaUrls.length > 1 && (
                            <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-1.5">
                                {mediaUrls.map((_, i) => (
                                    <button
                                        key={i}
                                        onClick={() => setSliderIdx(i)}
                                        className="rounded-full transition-all"
                                        style={{
                                            width: i === sliderIdx ? 20 : 6,
                                            height: 6,
                                            background: i === sliderIdx ? "#fff" : "rgba(255,255,255,0.4)",
                                        }}
                                    />
                                ))}
                            </div>
                        )}

                        {/* Media count badge */}
                        <div
                            className="absolute top-3 right-3 text-xs px-2.5 py-1 rounded-full font-semibold"
                            style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(8px)" }}
                        >
                            {sliderIdx + 1} / {mediaUrls.length}
                        </div>

                        {/* Main badge */}
                        {sliderIdx === 0 && (
                            <div
                                className="absolute top-3 left-3 text-xs px-2.5 py-1 rounded-full font-bold"
                                style={{ background: "rgba(124,58,237,0.9)" }}
                            >
                                ГЛАВНОЕ
                            </div>
                        )}

                        {/* Лайки к текущему фото */}
                        {(photoLikes[sliderIdx] ?? 0) > 0 && (
                            <div className="absolute bottom-10 left-3 flex gap-2">
                                <div className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ background: "rgba(239,68,68,0.85)", backdropFilter: "blur(6px)" }}>
                                    ❤️ {photoLikes[sliderIdx]}
                                </div>
                            </div>
                        )}

                        {/* Arrow taps */}
                        {sliderIdx > 0 && (
                            <button
                                onClick={() => setSliderIdx((i) => i - 1)}
                                className="absolute left-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full flex items-center justify-center"
                                style={{ background: "rgba(0,0,0,0.4)" }}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                                    <path d="M15 18l-6-6 6-6" />
                                </svg>
                            </button>
                        )}
                        {sliderIdx < mediaUrls.length - 1 && (
                            <button
                                onClick={() => setSliderIdx((i) => i + 1)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full flex items-center justify-center"
                                style={{ background: "rgba(0,0,0,0.4)" }}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                                    <path d="M9 18l6-6-6-6" />
                                </svg>
                            </button>
                        )}
                    </>
                ) : (
                    /* No media placeholder */
                    <button
                        onClick={() => setEditOpen(true)}
                        className="w-full h-full flex flex-col items-center justify-center gap-3 transition-all active:opacity-70"
                    >
                        <div
                            className="w-20 h-20 rounded-full flex items-center justify-center text-4xl"
                            style={{ background: "rgba(124,58,237,0.15)", border: "2px dashed rgba(124,58,237,0.4)" }}
                        >
                            📷
                        </div>
                        <p className="text-white/50 text-sm">Добавить фото или видео</p>
                    </button>
                )}
            </div>

            {/* ── User info ── */}
            <div className="px-4 mt-5 space-y-3">
                <div className="rounded-2xl p-4 space-y-3" style={{ background: "rgba(255,255,255,0.06)" }}>
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

                <ProfileAnswers userId={userId} />

                {/* Photo Likes Button */}
                <button
                    onClick={() => router.push(`/users/${userId}/photo-likes`)}
                    className="w-full rounded-2xl p-4 flex items-center gap-3 transition-all active:scale-[0.98]"
                    style={{
                        background: "linear-gradient(135deg, rgba(239,68,68,0.12), rgba(236,72,153,0.08))",
                        border: "1px solid rgba(239,68,68,0.2)",
                    }}
                >
                    <span className="text-2xl">❤️</span>
                    <div className="flex-1 text-left">
                        <div className="text-sm font-semibold text-white">Лайки на мои фото</div>
                        <div className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>Узнай кому нравишься</div>
                    </div>
                    <span style={{ color: "rgba(255,255,255,0.3)" }}>›</span>
                </button>

                <div className="rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.04)" }}>
                    <p className="text-sm text-white/40 text-center">
                        Для редактирования имени, города и описания — используй кнопку ⚙️ в боте
                    </p>
                </div>

                {/* Referral card */}
                <div className="rounded-2xl p-4 space-y-3" style={{ background: "linear-gradient(135deg, rgba(124,58,237,0.15), rgba(79,70,229,0.1))", border: "1px solid rgba(124,58,237,0.25)" }}>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-base">🔗</span>
                        <p className="text-sm font-semibold text-white">Реферальная программа</p>
                    </div>
                    <p className="text-xs text-white/50 leading-relaxed">
                        Приглашай друзей — получай <b className="text-purple-300">50%</b> с каждой их покупки
                    </p>

                    {(user.referral_balance ?? 0) > 0 && (
                        <div className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: "rgba(124,58,237,0.2)" }}>
                            <span className="text-sm">💰</span>
                            <span className="text-sm font-bold text-green-300">
                                Баланс: {(user.referral_balance ?? 0).toFixed(2)} ₽
                            </span>
                        </div>
                    )}

                    <button
                        onClick={() => {
                            const link = `https://t.me/LsJ_loveBot?start=ref_${userId}`;
                            if (navigator.clipboard) {
                                navigator.clipboard.writeText(link).then(() => {
                                    setRefCopied(true);
                                    setTimeout(() => setRefCopied(false), 2500);
                                });
                            }
                        }}
                        className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all"
                        style={{ background: refCopied ? "rgba(34,197,94,0.3)" : "rgba(124,58,237,0.4)", border: "1px solid rgba(124,58,237,0.4)" }}
                    >
                        {refCopied ? "✅ Ссылка скопирована!" : "📋 Скопировать реферальную ссылку"}
                    </button>

                    {(user.referral_balance ?? 0) > 0 && (
                        <a
                            href={`https://t.me/babymaxx?text=${encodeURIComponent("Здравствуйте, я хотел бы запросить вывод средств по реферальной системе LsJ_Love")}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-semibold transition-all"
                            style={{ background: "rgba(34,197,94,0.2)", border: "1px solid rgba(34,197,94,0.35)", color: "#86efac", textDecoration: "none" }}
                        >
                            💸 Запросить вывод средств
                        </a>
                    )}
                </div>
            </div>

            <BottomNav userId={userId} />

            {/* ── Edit Media Sheet ── */}
            {editOpen && (
                <div className="fixed inset-0 z-50 flex flex-col justify-end">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0"
                        style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
                        onClick={() => !uploading && !deleteIdx && setEditOpen(false)}
                    />

                    {/* Sheet */}
                    <div
                        className="relative rounded-t-3xl px-4 pb-8 pt-5 z-10"
                        style={{ background: "linear-gradient(180deg, #1a0a2e 0%, #0f0a1e 100%)", maxHeight: "85vh", overflowY: "auto" }}
                    >
                        {/* Handle */}
                        <div className="w-10 h-1 rounded-full mx-auto mb-5" style={{ background: "rgba(255,255,255,0.2)" }} />

                        <div className="flex items-center justify-between mb-1">
                            <h2 className="text-lg font-bold text-white">Медиа профиля</h2>
                            <button
                                onClick={() => setEditOpen(false)}
                                disabled={uploading || deleteIdx !== null}
                                className="text-white/40 hover:text-white transition-colors text-sm font-semibold px-3 py-1.5 rounded-xl"
                                style={{ background: "rgba(255,255,255,0.08)" }}
                            >
                                Готово
                            </button>
                        </div>
                        <p className="text-xs text-white/40 mb-5">До {MAX_MEDIA} фото и видео · нажми на слот, чтобы добавить или заменить</p>

                        {error && (
                            <div className="mb-4 px-3 py-2.5 rounded-xl text-sm text-red-300" style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }}>
                                {error}
                            </div>
                        )}

                        {/* 3x2 grid */}
                        <div className="grid grid-cols-3 gap-2.5">
                            {slots.map((_, i) => {
                                const hasItem = i < mediaUrls.length;
                                const isDeleting = deleteIdx === i;
                                const isUploading = uploading && pendingSlot === i;
                                const isVideo = hasItem && isVideoUrl(mediaUrls[i], mediaTypes[i]);

                                return (
                                    <div
                                        key={i}
                                        className="relative rounded-2xl overflow-hidden"
                                        style={{
                                            aspectRatio: "1",
                                            background: hasItem ? undefined : "rgba(255,255,255,0.04)",
                                            border: !hasItem ? "1.5px dashed rgba(255,255,255,0.12)" : "none",
                                        }}
                                    >
                                        {hasItem ? (
                                            <>
                                                {isVideo ? (
                                                    <video
                                                        src={mediaUrls[i]}
                                                        className="w-full h-full object-cover"
                                                        muted
                                                        playsInline
                                                    />
                                                ) : (
                                                    <img
                                                        src={mediaUrls[i]}
                                                        alt={`Медиа ${i + 1}`}
                                                        className="w-full h-full object-cover"
                                                        onError={(e) => {
                                                            const el = e.target as HTMLImageElement;
                                                            if (!el.src.endsWith("/placeholder.svg")) el.src = "/placeholder.svg";
                                                        }}
                                                    />
                                                )}

                                                {/* Video indicator */}
                                                {isVideo && (
                                                    <div className="absolute bottom-1.5 left-1.5 w-5 h-5 rounded-full flex items-center justify-center" style={{ background: "rgba(0,0,0,0.65)" }}>
                                                        <svg width="9" height="9" viewBox="0 0 24 24" fill="white">
                                                            <path d="M8 5v14l11-7z" />
                                                        </svg>
                                                    </div>
                                                )}

                                                {/* Main label */}
                                                {i === 0 && (
                                                    <div
                                                        className="absolute top-1.5 left-1.5 text-white font-bold rounded-md px-1.5 py-0.5"
                                                        style={{ fontSize: 8, background: "rgba(124,58,237,0.9)" }}
                                                    >
                                                        ГЛАВНОЕ
                                                    </div>
                                                )}

                                                {/* Replace tap area */}
                                                <button
                                                    onClick={() => openPicker(i)}
                                                    disabled={uploading || isDeleting}
                                                    className="absolute inset-0 opacity-0 hover:opacity-100 flex items-center justify-center transition-opacity"
                                                    style={{ background: "rgba(0,0,0,0.45)" }}
                                                >
                                                    {isUploading ? (
                                                        <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                                    ) : (
                                                        <span className="text-white text-xs font-semibold bg-black/40 px-2 py-1 rounded-lg">Заменить</span>
                                                    )}
                                                </button>

                                                {/* Delete button */}
                                                <button
                                                    onClick={() => deleteMedia(i)}
                                                    disabled={isDeleting || uploading}
                                                    className="absolute top-1.5 right-1.5 w-6 h-6 rounded-full flex items-center justify-center transition-all active:scale-90 z-10"
                                                    style={{ background: "rgba(220,38,38,0.85)" }}
                                                >
                                                    {isDeleting ? (
                                                        <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                                                    ) : (
                                                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                                                            <path d="M18 6L6 18M6 6l12 12" />
                                                        </svg>
                                                    )}
                                                </button>
                                            </>
                                        ) : (
                                            <button
                                                onClick={() => openPicker(i)}
                                                disabled={uploading || i > mediaUrls.length}
                                                className="w-full h-full flex flex-col items-center justify-center gap-1.5 transition-all active:scale-95"
                                            >
                                                {uploading && pendingSlot === i ? (
                                                    <div className="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
                                                ) : (
                                                    <>
                                                        <span className="text-2xl" style={{ opacity: i > mediaUrls.length ? 0.15 : 0.4 }}>+</span>
                                                        {i === mediaUrls.length && (
                                                            <span className="text-xs text-white/25">фото/видео</span>
                                                        )}
                                                    </>
                                                )}
                                            </button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        <p className="mt-4 text-center text-xs text-white/25">
                            Нажми на слот, чтобы добавить · красная кнопка — удалить
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
