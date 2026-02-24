"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
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
}

interface Comment {
    id: string;
    from_user: number;
    from_name: string;
    text: string;
    created_at: string;
}

interface PhotoMeta {
    count: number;
    liked_by_me: boolean;
}

export default function ViewProfilePage() {
    const params = useParams();
    const userId = params.users as string;
    const targetId = params.targetId as string;

    const [user, setUser] = useState<TargetUser | null>(null);
    const [loading, setLoading] = useState(true);
    const [currentPhoto, setCurrentPhoto] = useState(0);
    const [photoMeta, setPhotoMeta] = useState<Record<number, PhotoMeta>>({});
    const [likeLoading, setLikeLoading] = useState(false);
    const [comments, setComments] = useState<Comment[]>([]);
    const [commentText, setCommentText] = useState("");
    const [commentLoading, setCommentLoading] = useState(false);
    const [showComments, setShowComments] = useState(false);
    const [profileLiked, setProfileLiked] = useState(false);
    const [profileLikeLoading, setProfileLikeLoading] = useState(false);
    const [isMatch, setIsMatch] = useState(false);
    const touchStartX = useRef<number | null>(null);
    const commentsEndRef = useRef<HTMLDivElement>(null);
    const commentSubmitting = useRef(false); // prevent double submission

    const photos = user?.photos?.length
        ? user.photos.map((p) => p.startsWith("http") ? p : `${BackEnd_URL}${p}`)
        : user?.photo
            ? [`${BackEnd_URL}/api/v1/users/${targetId}/photo`]
            : ["/placeholder.svg"];

    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/users/${targetId}`)
            .then((r) => r.json())
            .then(setUser)
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, [targetId]);

    // Проверяем, уже ли лайкнул и есть ли матч — чтобы не показывать лишнюю кнопку лайка
    useEffect(() => {
        if (!userId || !targetId) return;
        fetch(`${BackEnd_URL}/api/v1/likes/${userId}/${targetId}`)
            .then((r) => r.json())
            .then((data) => {
                if (data.status === true) setProfileLiked(true);
            })
            .catch(() => {});
        // Проверяем матч
        fetch(`${BackEnd_URL}/api/v1/likes/matches/${userId}`)
            .then((r) => r.json())
            .then((data) => {
                const ids: number[] = (data.items ?? []).map((u: { telegram_id: number }) => u.telegram_id);
                if (ids.includes(parseInt(targetId))) setIsMatch(true);
            })
            .catch(() => {});
    }, [userId, targetId]);

    const fetchPhotoMeta = useCallback(async (index: number) => {
        if (!userId) return;
        try {
            const res = await fetch(
                `${BackEnd_URL}/api/v1/photo-interactions/likes/${targetId}/${index}?viewer_id=${userId}`
            );
            if (res.ok) {
                const data = await res.json();
                setPhotoMeta((prev) => ({ ...prev, [index]: { count: data.count, liked_by_me: data.liked_by_me } }));
            }
        } catch {}
    }, [targetId, userId]);

    useEffect(() => {
        if (user) fetchPhotoMeta(currentPhoto);
    }, [user, currentPhoto, fetchPhotoMeta]);

    const fetchComments = useCallback(async () => {
        try {
            const res = await fetch(
                `${BackEnd_URL}/api/v1/photo-interactions/comments/${targetId}/${currentPhoto}`
            );
            if (res.ok) {
                const data = await res.json();
                setComments(data.comments || []);
            }
        } catch {}
    }, [targetId, currentPhoto]);

    useEffect(() => {
        if (showComments) fetchComments();
    }, [showComments, fetchComments]);

    useEffect(() => {
        commentsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [comments]);

    const handlePhotoLike = async () => {
        if (likeLoading || !userId) return;
        setLikeLoading(true);
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
                setPhotoMeta((prev) => ({ ...prev, [currentPhoto]: { count: data.count, liked_by_me: data.liked_by_me } }));
            }
        } catch {} finally {
            setLikeLoading(false);
        }
    };

    const handleProfileLike = async () => {
        if (profileLikeLoading || !userId) return;
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

    const handleAddComment = async () => {
        if (!commentText.trim() || commentLoading || !userId) return;
        if (commentSubmitting.current) return; // strict guard against double fire
        commentSubmitting.current = true;
        setCommentLoading(true);
        const textToSend = commentText.trim();
        setCommentText(""); // clear input immediately to prevent re-submit
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/photo-interactions/comments`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    from_user: parseInt(userId),
                    owner_id: parseInt(targetId),
                    photo_index: currentPhoto,
                    text: textToSend,
                }),
            });
            if (res.ok) {
                const data = await res.json();
                // Deduplication: only add if not already present
                setComments((prev) => {
                    if (prev.some((c) => c.id === data.id)) return prev;
                    return [...prev, data];
                });
            } else {
                setCommentText(textToSend); // restore on error
            }
        } catch {
            setCommentText(textToSend); // restore on error
        } finally {
            setCommentLoading(false);
            commentSubmitting.current = false;
        }
    };

    const nextPhoto = () => setCurrentPhoto((p) => Math.min(p + 1, photos.length - 1));
    const prevPhoto = () => setCurrentPhoto((p) => Math.max(p - 1, 0));

    const handleTouchStart = (e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
    };
    const handleTouchEnd = (e: React.TouchEvent) => {
        if (touchStartX.current === null) return;
        const diff = touchStartX.current - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 40) diff > 0 ? nextPhoto() : prevPhoto();
        touchStartX.current = null;
    };

    const meta = photoMeta[currentPhoto];

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center" style={{ background: "#0f0f1a" }}>
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center" style={{ background: "#0f0f1a" }}>
                <p className="text-white/60">Профиль не найден</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen pb-8" style={{ background: "#0f0f1a", color: "#fff" }}>
            {/* Photo slider */}
            <div
                className="relative w-full"
                style={{ aspectRatio: "4/5", maxHeight: "72vh", background: "#1a1a2e" }}
                onTouchStart={handleTouchStart}
                onTouchEnd={handleTouchEnd}
            >
                <img
                    src={photos[currentPhoto]}
                    alt={user.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                        const img = e.target as HTMLImageElement;
                        if (!img.src.endsWith("/placeholder.svg")) img.src = "/placeholder.svg";
                    }}
                />

                {/* Gradient overlay bottom */}
                <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.2) 50%, transparent 100%)" }} />

                {/* Progress bars + photo counter */}
                {photos.length > 1 && (
                    <div className="absolute top-0 left-0 right-0 px-3 pt-3 z-10">
                        <div className="flex gap-1 mb-1.5">
                            {photos.map((_, i) => (
                                <div
                                    key={i}
                                    onClick={() => setCurrentPhoto(i)}
                                    className="rounded-full cursor-pointer transition-all duration-300"
                                    style={{
                                        height: 3,
                                        flex: 1,
                                        background: i === currentPhoto
                                            ? "#fff"
                                            : i < currentPhoto
                                            ? "rgba(255,255,255,0.55)"
                                            : "rgba(255,255,255,0.22)",
                                    }}
                                />
                            ))}
                        </div>
                        <div className="flex justify-end">
                            <span style={{
                                background: "rgba(0,0,0,0.45)",
                                backdropFilter: "blur(6px)",
                                color: "rgba(255,255,255,0.85)",
                                fontSize: 11,
                                fontWeight: 600,
                                padding: "2px 8px",
                                borderRadius: 20,
                            }}>
                                {currentPhoto + 1} / {photos.length}
                            </span>
                        </div>
                    </div>
                )}

                {/* Visible navigation arrows */}
                {photos.length > 1 && currentPhoto > 0 && (
                    <button
                        onClick={prevPhoto}
                        className="absolute left-2 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center transition-all active:scale-90"
                        style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(6px)" }}
                        aria-label="Prev"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                            <path d="M15 18l-6-6 6-6"/>
                        </svg>
                    </button>
                )}
                {photos.length > 1 && currentPhoto < photos.length - 1 && (
                    <button
                        onClick={nextPhoto}
                        className="absolute right-2 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center transition-all active:scale-90"
                        style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(6px)" }}
                        aria-label="Next"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                            <path d="M9 18l6-6-6-6"/>
                        </svg>
                    </button>
                )}

                {/* Photo like button */}
                <button
                    onClick={handlePhotoLike}
                    disabled={likeLoading}
                    className="absolute bottom-20 right-4 flex flex-col items-center gap-1 z-10"
                >
                    <div
                        className="w-12 h-12 rounded-full flex items-center justify-center backdrop-blur-sm transition-all active:scale-90 shadow-lg"
                        style={{
                            background: meta?.liked_by_me
                                ? "linear-gradient(135deg, #ef4444, #ec4899)"
                                : "rgba(255,255,255,0.18)",
                            boxShadow: meta?.liked_by_me ? "0 4px 16px rgba(239,68,68,0.4)" : "none",
                        }}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill={meta?.liked_by_me ? "#fff" : "none"} stroke="#fff" strokeWidth="2">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                        </svg>
                    </div>
                    {meta && meta.count > 0 && (
                        <span className="text-xs font-semibold text-white">{meta.count}</span>
                    )}
                </button>

                {/* Tap hint when multiple photos — show only if single photo hidden */}
                {photos.length > 1 && (
                    <div className="absolute bottom-20 left-4 z-10">
                        <span style={{
                            background: "rgba(0,0,0,0.4)",
                            backdropFilter: "blur(4px)",
                            color: "rgba(255,255,255,0.6)",
                            fontSize: 11,
                            padding: "3px 8px",
                            borderRadius: 12,
                        }}>
                            ← листай фото →
                        </span>
                    </div>
                )}

                {/* Name/age overlay */}
                <div className="absolute bottom-4 left-4 right-20">
                    <h1 className="text-2xl font-bold text-white drop-shadow">
                        {user.name}{user.age ? `, ${user.age}` : ""}
                    </h1>
                    {user.city && (
                        <p className="text-white/75 text-sm flex items-center gap-1 mt-0.5">
                            <span>📍</span>{user.city}
                        </p>
                    )}
                </div>
            </div>

            {/* Info section */}
            <div className="px-4 pt-4 space-y-4">
                {/* About */}
                {user.about && (
                    <div
                        className="rounded-2xl p-4"
                        style={{ background: "rgba(255,255,255,0.06)" }}
                    >
                        <p className="text-sm text-white/80 leading-relaxed">{user.about}</p>
                    </div>
                )}

                {/* Profile like button — скрываем если уже матч */}
                {isMatch ? (
                    <div
                        className="w-full py-3.5 rounded-2xl font-semibold text-base text-center"
                        style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)", color: "#fff" }}
                    >
                        💕 Взаимная симпатия — у вас матч!
                    </div>
                ) : (
                    <button
                        onClick={handleProfileLike}
                        disabled={profileLikeLoading || profileLiked}
                        className="w-full py-3.5 rounded-2xl font-semibold text-base transition-all active:scale-95 disabled:opacity-60"
                        style={{
                            background: profileLiked
                                ? "rgba(255,255,255,0.08)"
                                : "linear-gradient(135deg, #7c3aed, #ec4899)",
                            color: "#fff",
                        }}
                    >
                        {profileLiked ? "✓ Симпатия отправлена" : "💌 Лайкнуть анкету"}
                    </button>
                )}

                {/* Comments toggle */}
                <button
                    onClick={() => setShowComments((v) => !v)}
                    className="w-full py-3 rounded-2xl text-sm font-medium transition-all"
                    style={{ background: "rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.8)" }}
                >
                    {showComments ? "▲ Скрыть комментарии" : `💬 Комментарии к фото ${currentPhoto + 1}`}
                </button>

                {/* Comments section */}
                {showComments && (
                    <div className="space-y-3">
                        {comments.length === 0 && (
                            <p className="text-center text-white/40 text-sm py-4">Пока нет комментариев. Напиши первым!</p>
                        )}
                        {comments.map((c) => (
                            <div
                                key={c.id}
                                className="rounded-xl p-3"
                                style={{ background: "rgba(255,255,255,0.06)" }}
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs font-semibold text-purple-400">{c.from_name}</span>
                                    <span className="text-xs text-white/30">
                                        {c.created_at ? new Date(c.created_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" }) : ""}
                                    </span>
                                </div>
                                <p className="text-sm text-white/80">{c.text}</p>
                            </div>
                        ))}
                        <div ref={commentsEndRef} />

                        {/* Add comment */}
                        <div
                            className="flex gap-2 items-end rounded-2xl p-2"
                            style={{ background: "rgba(255,255,255,0.07)" }}
                        >
                            <textarea
                                value={commentText}
                                onChange={(e) => setCommentText(e.target.value)}
                                placeholder="Написать комментарий..."
                                rows={1}
                                maxLength={300}
                                className="flex-1 bg-transparent text-sm text-white placeholder-white/30 outline-none resize-none py-2 px-2 leading-relaxed"
                                style={{ maxHeight: 80, overflowY: "auto" }}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleAddComment();
                                    }
                                }}
                            />
                            <button
                                onClick={handleAddComment}
                                disabled={commentLoading || !commentText.trim()}
                                className="w-9 h-9 rounded-full flex items-center justify-center transition-all active:scale-90 disabled:opacity-30 flex-shrink-0"
                                style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)" }}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                                    <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
                                </svg>
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
