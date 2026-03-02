"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";

const BackEnd_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    imagePreview?: string;
    ts: number;
}

interface AdvisorStatus {
    is_vip: boolean;
    trial_active: boolean;
    trial_hours_left: number | null;
    trial_expired: boolean;
    vip_expired?: boolean;
}

const WELCOME_MSG: Message = {
    id: "welcome",
    role: "assistant",
    content:
        "Привет! 👋 Я твой AI Советник по общению.\n\n" +
        "Помогу тебе:\n" +
        "• Оживить застывший диалог\n" +
        "• Придумать что написать первым\n" +
        "• Разобраться в ситуации по скрину переписки\n\n" +
        "Пришли скриншот переписки или опиши ситуацию — дам конкретные варианты сообщений 🎯",
    ts: Date.now(),
};

export default function AiAdvisorPage() {
    const params = useParams();
    const router = useRouter();
    const userId = params.users as string;

    const [messages, setMessages] = useState<Message[]>([WELCOME_MSG]);
    const [input, setInput] = useState("");
    const [imageBase64, setImageBase64] = useState<string | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState<AdvisorStatus | null>(null);
    const [statusLoading, setStatusLoading] = useState(true);
    const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

    const bottomRef = useRef<HTMLDivElement>(null);
    const fileRef = useRef<HTMLInputElement>(null);
    const textRef = useRef<HTMLTextAreaElement>(null);

    const fetchStatus = useCallback(() => {
        if (!userId) return;
        fetch(`${BackEnd_URL}/api/v1/ai/dialog-advisor/status/${userId}`)
            .then((r) => r.json())
            .then((d: AdvisorStatus) => {
                setStatus(d);
                if (!d.is_vip && d.trial_active && d.trial_hours_left !== null) {
                    setSecondsLeft(Math.round(d.trial_hours_left * 3600));
                } else if (!d.is_vip && d.trial_expired) {
                    setSecondsLeft(0);
                }
            })
            .catch(() => setStatus(null));
    }, [userId]);

    // Загружаем статус
    useEffect(() => {
        if (!userId) return;
        setStatusLoading(true);
        fetch(`${BackEnd_URL}/api/v1/ai/dialog-advisor/status/${userId}`)
            .then((r) => r.json())
            .then((d: AdvisorStatus) => {
                setStatus(d);
                if (!d.is_vip && d.trial_active && d.trial_hours_left !== null) {
                    setSecondsLeft(Math.round(d.trial_hours_left * 3600));
                } else if (!d.is_vip && d.trial_expired) {
                    setSecondsLeft(0);
                }
            })
            .catch(() => setStatus(null))
            .finally(() => setStatusLoading(false));
    }, [userId]);

    // Таймер обратного отсчёта
    useEffect(() => {
        if (secondsLeft === null) return;
        if (secondsLeft <= 0) {
            // Пробный период истёк
            setStatus((prev) => prev ? { ...prev, trial_active: false, trial_expired: true, trial_hours_left: null } : prev);
            return;
        }
        const timer = setInterval(() => {
            setSecondsLeft((s) => {
                if (s === null || s <= 1) {
                    clearInterval(timer);
                    setStatus((prev) => prev ? { ...prev, trial_active: false, trial_expired: true, trial_hours_left: null } : prev);
                    return 0;
                }
                return s - 1;
            });
        }, 1000);
        return () => clearInterval(timer);
    }, [secondsLeft === null || secondsLeft <= 0]);  // eslint-disable-line

    // Обновляем с сервера каждые 5 минут для синхронизации
    useEffect(() => {
        if (!userId) return;
        const interval = setInterval(fetchStatus, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [fetchStatus]);

    // Восстанавливаем историю из localStorage
    useEffect(() => {
        try {
            const saved = localStorage.getItem(`ai_advisor_history_${userId}`);
            if (saved) {
                const parsed = JSON.parse(saved) as Message[];
                if (parsed.length > 0) setMessages([WELCOME_MSG, ...parsed]);
            }
        } catch { /* ignore */ }
    }, [userId]);

    // Сохраняем историю
    useEffect(() => {
        if (messages.length <= 1) return;
        try {
            const toSave = messages.slice(1, 51); // max 50 сообщений
            localStorage.setItem(`ai_advisor_history_${userId}`, JSON.stringify(toSave));
        } catch { /* ignore */ }
    }, [messages, userId]);

    // Автоскролл вниз
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const handleImageChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            const result = reader.result as string;
            // Сжимаем изображение перед отправкой
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement("canvas");
                const MAX_W = 1280;
                const MAX_H = 1280;
                let w = img.width;
                let h = img.height;
                if (w > MAX_W || h > MAX_H) {
                    const ratio = Math.min(MAX_W / w, MAX_H / h);
                    w = Math.round(w * ratio);
                    h = Math.round(h * ratio);
                }
                canvas.width = w;
                canvas.height = h;
                canvas.getContext("2d")?.drawImage(img, 0, 0, w, h);
                const compressed = canvas.toDataURL("image/jpeg", 0.8);
                setImagePreview(compressed);
                setImageBase64(compressed.split(",")[1] ?? "");
            };
            img.src = result;
        };
        reader.readAsDataURL(file);
        e.target.value = "";
    }, []);

    const clearImage = useCallback(() => {
        setImageBase64(null);
        setImagePreview(null);
    }, []);

    const sendMessage = useCallback(async () => {
        if (loading) return;
        if (!input.trim() && !imageBase64) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input.trim(),
            imagePreview: imagePreview ?? undefined,
            ts: Date.now(),
        };

        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        clearImage();
        setLoading(true);

        // История для контекста (без welcome, только последние 12)
        const history = messages
            .filter((m) => m.id !== "welcome")
            .slice(-12)
            .map((m) => ({ role: m.role, content: m.content }));

        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/ai/dialog-advisor`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: parseInt(userId),
                    message: userMsg.content,
                    image_base64: imageBase64,
                    history,
                }),
            });

            if (res.status === 403) {
                const aiMsg: Message = {
                    id: Date.now().toString(),
                    role: "assistant",
                    content: "🔒 Пробный период истёк.\n\nAI Советник доступен по подписке VIP. Перейди в раздел Premium, чтобы получить доступ.",
                    ts: Date.now(),
                };
                setMessages((prev) => [...prev, aiMsg]);
                // Обновляем статус
                setStatus((prev) => prev ? { ...prev, trial_active: false, trial_expired: true, trial_hours_left: null } : prev);
                return;
            }

            const data = await res.json();
            if (!res.ok) {
                const errDetail = data?.detail?.error || data?.detail || data?.error || `Ошибка сервера ${res.status}`;
                const errMsg: Message = {
                    id: Date.now().toString(),
                    role: "assistant",
                    content: `⚠️ ${errDetail}`,
                    ts: Date.now(),
                };
                setMessages((prev) => [...prev, errMsg]);
                return;
            }
            if (data.reply) {
                const aiMsg: Message = {
                    id: Date.now().toString(),
                    role: "assistant",
                    content: data.reply,
                    ts: Date.now(),
                };
                setMessages((prev) => [...prev, aiMsg]);
                if (data.trial_hours_left !== undefined) {
                    setStatus((prev) =>
                        prev ? { ...prev, trial_hours_left: data.trial_hours_left } : prev
                    );
                }
            } else {
                const errMsg: Message = {
                    id: Date.now().toString(),
                    role: "assistant",
                    content: "⚠️ Сервер не вернул ответ. Попробуй ещё раз.",
                    ts: Date.now(),
                };
                setMessages((prev) => [...prev, errMsg]);
            }
        } catch (e: any) {
            const errMsg: Message = {
                id: Date.now().toString(),
                role: "assistant",
                content: `⚠️ Ошибка соединения: ${e?.message || "попробуй ещё раз"}`,
                ts: Date.now(),
            };
            setMessages((prev) => [...prev, errMsg]);
        } finally {
            setLoading(false);
        }
    }, [loading, input, imageBase64, imagePreview, messages, userId, clearImage]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const clearHistory = () => {
        setMessages([WELCOME_MSG]);
        localStorage.removeItem(`ai_advisor_history_${userId}`);
    };

    // ── Locked screen ──────────────────────────────────────────────────────────
    if (!statusLoading && status?.trial_expired) {
        return (
            <div className="fixed inset-0 flex flex-col" style={{ background: "linear-gradient(135deg, #0f0f1a 0%, #1a0a2e 50%, #0a1628 100%)" }}>
                {/* Header */}
                <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10" style={{ paddingTop: 48 }}>
                    <button onClick={() => router.back()} className="text-white/60 hover:text-white transition-colors">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5M12 5l-7 7 7 7" />
                        </svg>
                    </button>
                    <span className="text-white font-semibold text-lg">🧠 AI Советник</span>
                </div>

                {/* Locked content */}
                <div className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-6">
                    <div className="w-24 h-24 rounded-full flex items-center justify-center text-5xl"
                         style={{ background: "rgba(139,92,246,0.15)", border: "2px solid rgba(139,92,246,0.3)" }}>
                        🔒
                    </div>
                    <div>
                        <h2 className="text-white text-2xl font-bold mb-2">
                            {status?.vip_expired ? "Подписка VIP истекла" : "Пробный период истёк"}
                        </h2>
                        <p className="text-white/60 text-sm leading-relaxed">
                            {status?.vip_expired
                                ? "Твой VIP закончился. Обнови подписку — и AI Советник снова будет с тобой 💫"
                                : <>AI Советник диалога доступен только пользователям с подпиской <span className="text-purple-400 font-semibold">VIP</span></>
                            }
                        </p>
                    </div>
                    <div className="w-full rounded-2xl p-4 space-y-2" style={{ background: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.2)" }}>
                        <p className="text-white/80 text-sm font-medium">С VIP подпиской ты получишь:</p>
                        {["🧠 Безлимитный AI Советник диалога", "💌 10 AI Icebreaker в день", "⚡ Буст анкеты каждую неделю", "👁 Кто смотрел твой профиль"].map((f) => (
                            <div key={f} className="flex items-center gap-2 text-sm text-white/70">
                                <span>{f}</span>
                            </div>
                        ))}
                    </div>
                    <button
                        onClick={() => router.push(`/users/${userId}/premium`)}
                        className="w-full py-4 rounded-2xl font-bold text-white text-lg transition-transform active:scale-95"
                        style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)" }}>
                        {status?.vip_expired ? "Обновить VIP →" : "Получить VIP →"}
                    </button>
                </div>
            </div>
        );
    }

    // ── Trial banner content ───────────────────────────────────────────────────
    const formatCountdown = (secs: number): string => {
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = secs % 60;
        if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
        return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    };

    const trialBanner = !statusLoading && status && !status.is_vip && status.trial_active && secondsLeft !== null && secondsLeft > 0 ? (
        <div className="flex items-center justify-between px-4 py-2 text-xs"
             style={{ background: "rgba(139,92,246,0.12)", borderBottom: "1px solid rgba(139,92,246,0.2)" }}>
            <span className="text-purple-300 font-mono">
                ⏱ Пробный доступ: <b>{formatCountdown(secondsLeft)}</b>
            </span>
            <button onClick={() => router.push(`/users/${userId}/premium`)}
                    className="text-purple-400 font-semibold hover:text-purple-300 transition-colors">
                Получить VIP
            </button>
        </div>
    ) : status?.is_vip ? (
        <div className="px-4 py-1.5 text-center text-xs text-purple-400/70"
             style={{ background: "rgba(139,92,246,0.06)", borderBottom: "1px solid rgba(139,92,246,0.1)" }}>
            💎 VIP активен — безлимитный доступ (до окончания подписки)
        </div>
    ) : null;

    // ── Main chat ──────────────────────────────────────────────────────────────
    return (
        <div className="fixed inset-0 flex flex-col"
             style={{ background: "linear-gradient(135deg, #0f0f1a 0%, #1a0a2e 50%, #0a1628 100%)" }}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 flex-shrink-0"
                 style={{ paddingTop: 48 }}>
                <div className="flex items-center gap-3">
                    <button onClick={() => router.back()} className="text-white/60 hover:text-white transition-colors">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5M12 5l-7 7 7 7" />
                        </svg>
                    </button>
                    <div className="flex items-center gap-2">
                        <div className="w-9 h-9 rounded-full flex items-center justify-center text-xl flex-shrink-0"
                             style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)" }}>
                            🧠
                        </div>
                        <div>
                            <div className="text-white font-semibold text-sm leading-tight">AI Советник</div>
                            <div className="text-white/40 text-xs leading-tight">Помогу с диалогом</div>
                        </div>
                    </div>
                </div>
                {messages.length > 1 && (
                    <button onClick={clearHistory} className="text-white/30 hover:text-white/60 transition-colors text-xs">
                        Очистить
                    </button>
                )}
            </div>

            {/* Trial banner */}
            {trialBanner}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
                 style={{ paddingBottom: imagePreview ? "180px" : "90px" }}>
                {messages.map((msg) => (
                    <div key={msg.id}
                         className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} gap-2`}>
                        {msg.role === "assistant" && (
                            <div className="w-8 h-8 rounded-full flex items-center justify-center text-base flex-shrink-0 mt-1"
                                 style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)" }}>
                                🧠
                            </div>
                        )}
                        <div className={`max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}>
                            {msg.imagePreview && (
                                <img src={msg.imagePreview} alt="скриншот"
                                     className="rounded-2xl max-w-full max-h-48 object-cover"
                                     style={{ border: "1px solid rgba(255,255,255,0.1)" }} />
                            )}
                            {msg.content && (
                                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                                    msg.role === "user"
                                        ? "rounded-tr-sm text-white"
                                        : "rounded-tl-sm text-white/90"
                                }`}
                                     style={msg.role === "user"
                                         ? { background: "linear-gradient(135deg, #7c3aed, #a855f7)" }
                                         : { background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.08)" }}>
                                    {msg.content}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* Typing indicator */}
                {loading && (
                    <div className="flex justify-start gap-2">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-base flex-shrink-0"
                             style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)" }}>
                            🧠
                        </div>
                        <div className="px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1.5"
                             style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.08)" }}>
                            <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                            <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                            <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                        </div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Input area */}
            <div className="fixed bottom-0 left-0 right-0 flex-shrink-0 border-t border-white/10"
                 style={{ background: "rgba(15,10,30,0.95)", backdropFilter: "blur(20px)", paddingBottom: "max(12px, env(safe-area-inset-bottom))" }}>

                {/* Image preview */}
                {imagePreview && (
                    <div className="px-4 pt-3 flex items-start gap-2">
                        <div className="relative">
                            <img src={imagePreview} alt="preview"
                                 className="w-16 h-16 rounded-xl object-cover"
                                 style={{ border: "1px solid rgba(139,92,246,0.4)" }} />
                            <button onClick={clearImage}
                                    className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center leading-none">
                                ×
                            </button>
                        </div>
                        <span className="text-white/40 text-xs mt-1">Скриншот добавлен</span>
                    </div>
                )}

                {/* Hints */}
                {messages.length === 1 && !imagePreview && (
                    <div className="px-4 pt-3 flex gap-2 overflow-x-auto scrollbar-hide">
                        {[
                            "📸 Пришли скриншот переписки",
                            "💬 Диалог завис, что написать?",
                            "🤔 Как начать разговор?",
                        ].map((hint) => (
                            <button key={hint}
                                    onClick={() => setInput(hint.replace(/^[^\s]+\s/, ""))}
                                    className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs text-white/60 border border-white/10 hover:border-purple-500/50 hover:text-purple-300 transition-colors whitespace-nowrap">
                                {hint}
                            </button>
                        ))}
                    </div>
                )}

                <div className="flex items-end gap-2 px-4 pt-2 pb-1">
                    {/* Image upload */}
                    <button onClick={() => fileRef.current?.click()}
                            className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-colors"
                            style={{ background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.3)" }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(167,139,250,1)" strokeWidth="2">
                            <rect x="3" y="3" width="18" height="18" rx="3" />
                            <circle cx="8.5" cy="8.5" r="1.5" />
                            <path d="M21 15l-5-5L5 21" />
                        </svg>
                    </button>
                    <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageChange} />

                    {/* Text input */}
                    <textarea
                        ref={textRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Опиши ситуацию или пришли скрин..."
                        rows={1}
                        className="flex-1 bg-transparent text-white text-sm placeholder-white/30 outline-none resize-none leading-relaxed py-2.5"
                        style={{ maxHeight: "100px", overflowY: "auto" }}
                    />

                    {/* Send button */}
                    <button
                        onClick={sendMessage}
                        disabled={loading || (!input.trim() && !imageBase64)}
                        className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all active:scale-90 disabled:opacity-30"
                        style={{ background: input.trim() || imageBase64
                            ? "linear-gradient(135deg, #7c3aed, #a855f7)"
                            : "rgba(139,92,246,0.15)" }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                            <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
