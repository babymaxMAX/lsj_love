"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";

// ─── Types ─────────────────────────────────────────────────────────────────

interface ProfileMatch {
    telegram_id: number;
    name: string;
    age?: number;
    city?: string;
    about?: string;
    photos: string[];
    photo?: string;
    username?: string;
    last_seen?: string;
    reasons?: string[];
}

type CardState = "idle" | "liked" | "skipped";

interface MatchCard {
    profile: ProfileMatch;
    state: CardState;
}

interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    cards?: MatchCard[];
    loading?: boolean;
    parsed_summary?: string;
    has_more?: boolean;
}

// ─── Helpers ───────────────────────────────────────────────────────────────

function getPhotoUrl(p: ProfileMatch): string {
    // Всегда используем API-эндпоинт — он сам редиректит на S3 (presigned URL)
    return `${BackEnd_URL}/api/v1/users/${p.telegram_id}/photo/0`;
}

function getOnlineDot(lastSeen?: string): string {
    if (!lastSeen) return "#6b7280";
    const ls = lastSeen.includes("+") || lastSeen.endsWith("Z") ? lastSeen : lastSeen + "Z";
    const min = (Date.now() - new Date(ls).getTime()) / 60000;
    if (isNaN(min)) return "#6b7280";
    if (min < 5) return "#22c55e";
    if (min < 60) return "#f59e0b";
    return "#6b7280";
}

// ─── Profile Card Component ────────────────────────────────────────────────

function ProfileCard({
    card,
    userId,
    onLike,
    onSkip,
}: {
    card: MatchCard;
    userId: string;
    onLike: () => void;
    onSkip: () => void;
}) {
    const { profile, state } = card;
    const [imgError, setImgError] = useState(false);
    const photoUrl = imgError ? "/placeholder.svg" : getPhotoUrl(profile);
    const dot = getOnlineDot(profile.last_seen);

    if (state === "skipped") return null;

    if (state === "liked") {
        return (
            <div
                className="rounded-2xl px-4 py-3 text-center text-sm font-medium"
                style={{ background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.3)", color: "#86efac" }}
            >
                ❤️ Лайк отправлен {profile.name}!
            </div>
        );
    }

    return (
        <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
        >
            {/* Photo */}
            <div className="relative w-full" style={{ aspectRatio: "3/4", maxHeight: "260px" }}>
                <img
                    src={photoUrl}
                    alt={profile.name}
                    className="w-full h-full object-cover"
                    onError={() => setImgError(true)}
                />
                {/* Online dot */}
                <div
                    className="absolute top-2 right-2 w-3 h-3 rounded-full"
                    style={{ background: dot, border: "2px solid #0f0f1a" }}
                />
                {/* Gradient overlay */}
                <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-black/80 to-transparent" />
                <div className="absolute bottom-3 left-3 text-white">
                    <p className="font-bold text-base leading-tight">
                        {profile.name}{profile.age ? `, ${profile.age}` : ""}
                    </p>
                    {profile.city && (
                        <p className="text-xs opacity-70">📍 {profile.city}</p>
                    )}
                </div>
            </div>

            {/* About */}
            {profile.about && (
                <div className="px-3 py-2">
                    <p className="text-xs text-white/60 line-clamp-2">{profile.about}</p>
                </div>
            )}
            {/* Почему подходит */}
            {profile.reasons && profile.reasons.length > 0 && (
                <div className="px-3 py-1">
                    <p className="text-xs" style={{ color: "rgba(124,58,237,0.9)" }}>
                        Подходит: {profile.reasons.join(", ")}
                    </p>
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 px-3 pb-3 pt-1">
                <button
                    onClick={onSkip}
                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all active:scale-95"
                    style={{ background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.5)" }}
                >
                    👎 Пропустить
                </button>
                <button
                    onClick={onLike}
                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all active:scale-95"
                    style={{ background: "linear-gradient(135deg, #ec4899, #ef4444)", color: "#fff" }}
                >
                    ❤️ Лайк
                </button>
            </div>
        </div>
    );
}

// ─── Chat Message Component ─────────────────────────────────────────────────

function ChatBubble({
    msg,
    userId,
    onLike,
    onSkip,
    onMoreSimilar,
}: {
    msg: ChatMessage;
    userId: string;
    onLike: (msgId: string, profileId: number) => void;
    onSkip: (msgId: string, profileId: number) => void;
    onMoreSimilar?: () => void;
}) {
    const isUser = msg.role === "user";

    if (isUser) {
        return (
            <div className="flex justify-end">
                <div
                    className="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm text-white"
                    style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
                >
                    {msg.content}
                </div>
            </div>
        );
    }

    if (msg.loading) {
        return (
            <div className="flex items-start gap-2">
                <div
                    className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-base"
                    style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
                >
                    🤖
                </div>
                <div
                    className="px-4 py-3 rounded-2xl rounded-tl-sm"
                    style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)" }}
                >
                    <div className="flex gap-1 items-center">
                        {[0, 1, 2].map((i) => (
                            <div
                                key={i}
                                className="w-2 h-2 rounded-full bg-purple-400 animate-bounce"
                                style={{ animationDelay: `${i * 0.15}s` }}
                            />
                        ))}
                        <span className="text-white/50 text-xs ml-2">AI ищет лучших для тебя...</span>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-start gap-2">
            <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-base flex-shrink-0"
                style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
            >
                🤖
            </div>
            <div className="flex-1 min-w-0 flex flex-col gap-3">
                {msg.parsed_summary && (
                    <div
                        className="px-3 py-2 rounded-xl text-xs"
                        style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.25)", color: "rgba(255,255,255,0.8)" }}
                    >
                        {msg.parsed_summary}
                    </div>
                )}
                {msg.content && (
                    <div
                        className="px-4 py-3 rounded-2xl rounded-tl-sm text-sm text-white/90 leading-relaxed"
                        style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)" }}
                    >
                        {msg.content}
                    </div>
                )}
                {msg.cards && msg.cards.length > 0 && (
                    <div className="flex flex-col gap-3">
                        {msg.cards.map((card) => (
                            <ProfileCard
                                key={card.profile.telegram_id}
                                card={card}
                                userId={userId}
                                onLike={() => onLike(msg.id, card.profile.telegram_id)}
                                onSkip={() => onSkip(msg.id, card.profile.telegram_id)}
                            />
                        ))}
                    </div>
                )}
                {msg.cards && msg.cards.length === 0 && !msg.content && (
                    <div
                        className="px-4 py-3 rounded-2xl rounded-tl-sm text-sm text-white/60"
                        style={{ background: "rgba(255,255,255,0.07)" }}
                    >
                        😔 Подходящих анкет не найдено. Попробуй изменить критерии.
                    </div>
                )}
                {msg.has_more && onMoreSimilar && (
                    <button
                        onClick={onMoreSimilar}
                        className="px-4 py-2.5 rounded-xl text-sm font-medium transition-all active:scale-95 w-fit"
                        style={{ background: "rgba(124,58,237,0.2)", border: "1px solid rgba(124,58,237,0.4)", color: "#a78bfa" }}
                    >
                        🔄 Ещё похожие
                    </button>
                )}
            </div>
        </div>
    );
}

// ─── Welcome suggestions ───────────────────────────────────────────────────

const SUGGESTIONS = [
    "Хочу познакомиться с девушкой 20-25 лет из Москвы, творческой и весёлой",
    "Ищу парня спортивного телосложения, который любит путешествия",
    "Хочу найти кого-то серьёзного для отношений, 25-30 лет",
    "Познакомлюсь с человеком, у которого добрая улыбка и интересное хобби",
];

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function AiMatchmakingPage() {
    const params = useParams();
    const router = useRouter();
    const userId = params.users as string;

    const [shownIds, setShownIds] = useState<number[]>([]);

    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: "welcome",
            role: "assistant",
            content:
                "Привет! 🤖 Я AI-сваха.\n\n" +
                "Расскажи, кого ищешь — возраст, характер, внешность, интересы. " +
                "Я проанализирую анкеты и фотографии и подберу лучших кандидатов специально для тебя! 💫",
        },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [conversation, setConversation] = useState<{ role: string; content: string }[]>([]);

    const bottomRef = useRef<HTMLDivElement>(null);
    const textRef = useRef<HTMLTextAreaElement>(null);

    // Scroll to bottom on new message
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Ping
    useEffect(() => {
        const ping = () => fetch(`${BackEnd_URL}/api/v1/users/${userId}/ping`, { method: "POST" }).catch(() => {});
        ping();
        const iv = setInterval(ping, 60_000);
        return () => clearInterval(iv);
    }, [userId]);

    const sendMessage = useCallback(async (text?: string) => {
        const userText = (text ?? input).trim();
        if (!userText || loading) return;

        setInput("");

        const userMsgId = `u-${Date.now()}`;
        const loadingMsgId = `l-${Date.now()}`;

        const userMsg: ChatMessage = { id: userMsgId, role: "user", content: userText };
        const loadingMsg: ChatMessage = { id: loadingMsgId, role: "assistant", content: "", loading: true };

        setMessages((prev) => [...prev, userMsg, loadingMsg]);
        setLoading(true);

        const newConversation = [...conversation, { role: "user", content: userText }];

        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/ai/matchmaking`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: parseInt(userId),
                    message: userText,
                    conversation: conversation,
                    shown_ids: shownIds,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: { error: "Ошибка сервера" } }));
                const errText = err?.detail?.error ?? "Что-то пошло не так. Попробуй ещё раз.";
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === loadingMsgId
                            ? { ...m, loading: false, content: `⚠️ ${errText}` }
                            : m
                    )
                );
                return;
            }

            const data = await res.json();
            const reply: string = data.reply ?? "";
            const matches: ProfileMatch[] = (data.matches ?? []).map((m: Record<string, unknown>) => ({
                ...m,
                reasons: m.reasons as string[] | undefined,
            }));
            const parsedSummary: string = data.parsed_summary ?? "";
            const hasMore: boolean = data.has_more ?? false;

            const cards: MatchCard[] = matches.map((p) => ({ profile: p, state: "idle" as CardState }));

            // Трекаем показанные ID — чтобы при следующем запросе AI показал других
            if (matches.length > 0) {
                setShownIds((prev) => {
                    const newIds = matches.map((p: ProfileMatch) => p.telegram_id);
                    return [...new Set([...prev, ...newIds])];
                });
            }

            const assistantMsg: ChatMessage = {
                id: loadingMsgId,
                role: "assistant",
                content: reply,
                cards,
                loading: false,
                parsed_summary: parsedSummary || undefined,
                has_more: hasMore,
            };

            setMessages((prev) =>
                prev.map((m) => (m.id === loadingMsgId ? assistantMsg : m))
            );

            // Обновляем историю разговора (без служебных пометок для AI)
            setConversation([
                ...newConversation,
                { role: "assistant", content: reply },
            ]);
        } catch {
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === loadingMsgId
                        ? { ...m, loading: false, content: "⚠️ Ошибка подключения. Проверь интернет и попробуй снова." }
                        : m
                )
            );
        } finally {
            setLoading(false);
        }
    }, [input, loading, userId, conversation]);

    const handleLike = useCallback(async (msgId: string, profileId: number) => {
        // Оптимистичное обновление UI
        setMessages((prev) =>
            prev.map((m) =>
                m.id === msgId
                    ? {
                        ...m,
                        cards: m.cards?.map((c) =>
                            c.profile.telegram_id === profileId ? { ...c, state: "liked" as CardState } : c
                        ),
                    }
                    : m
            )
        );
        // Отправляем лайк на бэкенд
        try {
            await fetch(`${BackEnd_URL}/api/v1/likes/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ from_user: parseInt(userId), to_user: profileId }),
            });
        } catch {
            // Тихая ошибка — UI уже обновился
        }
    }, [userId]);

    const handleSkip = useCallback((msgId: string, profileId: number) => {
        setMessages((prev) =>
            prev.map((m) =>
                m.id === msgId
                    ? {
                        ...m,
                        cards: m.cards?.map((c) =>
                            c.profile.telegram_id === profileId ? { ...c, state: "skipped" as CardState } : c
                        ),
                    }
                    : m
            )
        );
    }, []);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const handleSuggestion = (s: string) => {
        sendMessage(s);
    };

    const showSuggestions = messages.length === 1; // только при первом открытии

    return (
        <div className="flex flex-col h-screen" style={{ background: "#0f0f1a", color: "#fff" }}>
            {/* Header */}
            <div
                className="flex-shrink-0 flex items-center gap-3 px-4 py-3"
                style={{
                    background: "rgba(15,15,26,0.95)",
                    backdropFilter: "blur(12px)",
                    borderBottom: "1px solid rgba(255,255,255,0.07)",
                }}
            >
                <button
                    onClick={() => router.back()}
                    className="w-9 h-9 rounded-full flex items-center justify-center transition-all active:scale-90 flex-shrink-0"
                    style={{ background: "rgba(255,255,255,0.1)" }}
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                        <path d="M19 12H5M12 5l-7 7 7 7" />
                    </svg>
                </button>
                <div className="flex items-center gap-2">
                    <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-base"
                        style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
                    >
                        🤖
                    </div>
                    <div>
                        <p className="font-bold text-sm leading-tight">AI Подбор</p>
                        <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
                            Анализирует фото и описания
                        </p>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
                {messages.map((msg) => (
                    <ChatBubble
                        key={msg.id}
                        msg={msg}
                        userId={userId}
                        onLike={handleLike}
                        onSkip={handleSkip}
                        onMoreSimilar={msg.has_more ? () => sendMessage("Покажи ещё похожих") : undefined}
                    />
                ))}

                {/* Suggestions — показываем только в начале */}
                {showSuggestions && (
                    <div className="flex flex-col gap-2 mt-2">
                        <p className="text-xs text-white/40 text-center">Попробуй написать:</p>
                        {SUGGESTIONS.map((s, i) => (
                            <button
                                key={i}
                                onClick={() => handleSuggestion(s)}
                                className="text-left px-3 py-2.5 rounded-2xl text-xs text-white/70 transition-all active:scale-95"
                                style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.25)" }}
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div
                className="flex-shrink-0 px-3 py-3 flex items-end gap-2"
                style={{
                    background: "rgba(15,15,26,0.95)",
                    backdropFilter: "blur(12px)",
                    borderTop: "1px solid rgba(255,255,255,0.07)",
                    paddingBottom: "max(12px, env(safe-area-inset-bottom))",
                }}
            >
                <textarea
                    ref={textRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Опиши, кого ищешь..."
                    rows={1}
                    className="flex-1 resize-none rounded-2xl px-4 py-3 text-sm text-white outline-none"
                    style={{
                        background: "rgba(255,255,255,0.08)",
                        border: "1px solid rgba(255,255,255,0.12)",
                        maxHeight: "120px",
                        lineHeight: "1.4",
                    }}
                    disabled={loading}
                />
                <button
                    onClick={() => sendMessage()}
                    disabled={!input.trim() || loading}
                    className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 transition-all active:scale-90 disabled:opacity-40"
                    style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                        <path d="M22 2L11 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M22 2L15 22 11 13 2 9l20-7z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
