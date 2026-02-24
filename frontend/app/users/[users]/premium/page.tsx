"use client";
import { useState, useEffect, useRef } from "react";
import { BottomNav } from "@/components/bottom-nav";
import { BackEnd_URL } from "@/config/url";

type Product = "premium" | "vip" | "superlike";
type Method  = "sbp" | "crypto";

interface PaymentData {
    transaction_id: string;
    method: Method;
    product: string;
    amount: number;
    redirect_url?: string;
    expires_in?: string;
}

const PLANS = [
    {
        id: "premium" as Product,
        name: "Premium",
        emoji: "⭐",
        stars: 500,
        rub: 299,
        period: "в месяц",
        badge: "Популярный",
        gradient: "linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)",
        accentColor: "#f59e0b",
        features: [
            { icon: "❤️", text: "Безлимитные лайки" },
            { icon: "👁", text: "Кто тебя лайкнул" },
            { icon: "↩️", text: "Откат свайпа" },
            { icon: "💫", text: "1 суперлайк в день" },
        ],
    },
    {
        id: "vip" as Product,
        name: "VIP",
        emoji: "💎",
        stars: 1500,
        rub: 799,
        period: "в месяц",
        badge: "Максимум",
        gradient: "linear-gradient(135deg, #7c3aed 0%, #db2777 100%)",
        accentColor: "#7c3aed",
        features: [
            { icon: "✅", text: "Всё из Premium" },
            { icon: "🤖", text: "AI Icebreaker ×10/день" },
            { icon: "🚀", text: "Буст профиля ×3/нед" },
            { icon: "🏆", text: "Приоритет в поиске" },
        ],
    },
    {
        id: "superlike" as Product,
        name: "Суперлайк",
        emoji: "💫",
        stars: 50,
        rub: 49,
        period: "разово",
        badge: null,
        gradient: "linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)",
        accentColor: "#0ea5e9",
        features: [
            { icon: "🔝", text: "Твой профиль — первым" },
            { icon: "🔔", text: "Уведомление получателю" },
        ],
    },
];

// ── Экран успеха ─────────────────────────────────────────────────────────────
function SuccessScreen({ product, onClose }: { product: string; onClose: () => void }) {
    const p = PLANS.find(x => x.id === product);
    return (
        <div style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 24px", textAlign: "center", background: "var(--tg-theme-bg-color, #0f0f0f)" }}>
            <div style={{ fontSize: 72, marginBottom: 24, animation: "pop 0.4s ease" }}>🎉</div>
            <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8, color: "var(--tg-theme-text-color, #fff)" }}>
                Оплата прошла!
            </h2>
            <p style={{ color: "var(--tg-theme-hint-color, #999)", marginBottom: 32, fontSize: 15 }}>
                {p ? `${p.emoji} ${p.name}` : product} активирован{product === "superlike" ? "" : " на 30 дней"}
            </p>
            <button onClick={onClose} style={{ padding: "14px 40px", borderRadius: 20, background: "linear-gradient(135deg, #7c3aed, #db2777)", color: "#fff", fontWeight: 700, fontSize: 16, border: "none", cursor: "pointer" }}>
                Отлично ✓
            </button>
        </div>
    );
}

// ── Экран ожидания/оплаты ─────────────────────────────────────────────────────
function PaymentScreen({ data, status, onBack, userId }: { data: PaymentData; status: string; onBack: () => void; userId: string }) {
    const openPayment = () => {
        if (!data.redirect_url) return;
        const tg = (window as any).Telegram?.WebApp;
        if (tg?.openLink) {
            tg.openLink(data.redirect_url);
        } else {
            window.open(data.redirect_url, "_blank");
        }
    };

    const methodLabel = data.method === "sbp" ? "📱 СБП" : "₿ Крипто";
    const p = PLANS.find(x => x.id === data.product);

    return (
        <div style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", background: "var(--tg-theme-bg-color, #0f0f0f)" }}>
            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "calc(env(safe-area-inset-top) + 16px) 16px 16px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                <button onClick={onBack} style={{ width: 36, height: 36, borderRadius: 12, background: "rgba(255,255,255,0.08)", border: "none", color: "var(--tg-theme-text-color, #fff)", fontSize: 18, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    ←
                </button>
                <span style={{ fontWeight: 700, fontSize: 17, color: "var(--tg-theme-text-color, #fff)" }}>{methodLabel}</span>
            </div>

            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
                {/* Продукт */}
                <div style={{ background: "rgba(255,255,255,0.05)", borderRadius: 20, padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                        <div style={{ fontSize: 13, color: "var(--tg-theme-hint-color, #999)", marginBottom: 4 }}>Тариф</div>
                        <div style={{ fontWeight: 700, fontSize: 16, color: "var(--tg-theme-text-color, #fff)" }}>{p ? `${p.emoji} ${p.name}` : data.product}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 13, color: "var(--tg-theme-hint-color, #999)", marginBottom: 4 }}>Сумма</div>
                        <div style={{ fontWeight: 800, fontSize: 22, color: "#fff" }}>{data.amount} ₽</div>
                    </div>
                </div>

                {/* Статус */}
                {status === "polling" && (
                    <div style={{ background: "rgba(234,179,8,0.1)", border: "1px solid rgba(234,179,8,0.3)", borderRadius: 16, padding: "12px 16px", display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={{ fontSize: 20 }}>⏳</span>
                        <div>
                            <div style={{ fontWeight: 600, fontSize: 14, color: "#eab308" }}>Ожидаем оплату...</div>
                            <div style={{ fontSize: 12, color: "rgba(234,179,8,0.7)" }}>Проверяем каждые 5 секунд</div>
                        </div>
                    </div>
                )}

                {/* Инструкция СБП */}
                {data.method === "sbp" && (
                    <div style={{ background: "rgba(255,255,255,0.05)", borderRadius: 20, padding: 20 }}>
                        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: "var(--tg-theme-text-color, #fff)" }}>Как оплатить через СБП:</div>
                        {[
                            "Нажми кнопку «Открыть СБП» ниже",
                            "Выбери свой банк на странице оплаты",
                            "Подтверди перевод в приложении банка",
                        ].map((step, i) => (
                            <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12, alignItems: "flex-start" }}>
                                <div style={{ minWidth: 26, height: 26, borderRadius: "50%", background: "rgba(5,150,105,0.2)", border: "1px solid rgba(5,150,105,0.4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#10b981" }}>
                                    {i + 1}
                                </div>
                                <div style={{ fontSize: 14, color: "var(--tg-theme-text-color, #ccc)", paddingTop: 3 }}>{step}</div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Инструкция Крипто */}
                {data.method === "crypto" && (
                    <div style={{ background: "rgba(255,255,255,0.05)", borderRadius: 20, padding: 20 }}>
                        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: "var(--tg-theme-text-color, #fff)" }}>Как оплатить криптовалютой:</div>
                        {[
                            "Нажми «Открыть страницу оплаты»",
                            "Скопируй адрес кошелька USDT (TRC-20)",
                            "Переведи точную сумму со своего кошелька",
                            "Дождись подтверждения — это может занять ~5 мин",
                        ].map((step, i) => (
                            <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12, alignItems: "flex-start" }}>
                                <div style={{ minWidth: 26, height: 26, borderRadius: "50%", background: "rgba(249,115,22,0.15)", border: "1px solid rgba(249,115,22,0.35)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#f97316" }}>
                                    {i + 1}
                                </div>
                                <div style={{ fontSize: 14, color: "var(--tg-theme-text-color, #ccc)", paddingTop: 3 }}>{step}</div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Срок действия */}
                {data.expires_in && (
                    <div style={{ textAlign: "center", fontSize: 13, color: "#f97316" }}>
                        ⏱ Платёж действителен: <b>{data.expires_in}</b>
                    </div>
                )}

                {/* Кнопка открытия */}
                {data.redirect_url && (
                    <button onClick={openPayment} style={{ width: "100%", padding: "16px 0", borderRadius: 20, background: data.method === "sbp" ? "linear-gradient(135deg, #059669, #10b981)" : "linear-gradient(135deg, #f97316, #eab308)", color: "#fff", fontWeight: 700, fontSize: 16, border: "none", cursor: "pointer", boxShadow: data.method === "sbp" ? "0 8px 24px rgba(16,185,129,0.3)" : "0 8px 24px rgba(234,179,8,0.3)" }}>
                        {data.method === "sbp" ? "📱 Открыть СБП" : "₿ Открыть страницу оплаты"}
                    </button>
                )}

                <button onClick={onBack} style={{ width: "100%", padding: "13px 0", borderRadius: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", color: "var(--tg-theme-hint-color, #999)", fontWeight: 600, fontSize: 14, cursor: "pointer" }}>
                    ← Вернуться назад
                </button>
            </div>

            <div style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 80px)" }} />
            <BottomNav userId={userId} />
        </div>
    );
}

// ── Карточка плана ─────────────────────────────────────────────────────────
function PlanCard({ plan, onSelect }: { plan: typeof PLANS[0]; onSelect: (p: Product, m: Method) => void }) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState<string | null>(null);

    const handlePay = async (method: Method) => {
        setLoading(method);
        await onSelect(plan.id, method);
        setLoading(null);
    };

    return (
        <div style={{ borderRadius: 24, overflow: "hidden", border: open ? "1.5px solid rgba(255,255,255,0.2)" : "1.5px solid rgba(255,255,255,0.06)", transition: "all 0.2s" }}>
            {/* Шапка */}
            <button onClick={() => setOpen(!open)} style={{ width: "100%", background: plan.gradient, padding: "18px 20px", border: "none", cursor: "pointer", textAlign: "left", display: "block" }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                    <div>
                        {plan.badge && (
                            <div style={{ display: "inline-block", background: "rgba(0,0,0,0.25)", borderRadius: 100, padding: "3px 10px", fontSize: 11, fontWeight: 700, color: "#fff", marginBottom: 8, backdropFilter: "blur(4px)" }}>
                                {plan.badge}
                            </div>
                        )}
                        <div style={{ fontSize: 26, fontWeight: 900, color: "#fff", marginBottom: 4 }}>
                            {plan.emoji} {plan.name}
                        </div>
                        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                            <span style={{ fontSize: 24, fontWeight: 800, color: "#fff" }}>{plan.rub} ₽</span>
                            <span style={{ fontSize: 13, color: "rgba(255,255,255,0.7)" }}>{plan.period}</span>
                            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>· {plan.stars} ⭐</span>
                        </div>
                    </div>
                    <div style={{ fontSize: 20, color: "rgba(255,255,255,0.8)", marginTop: 4, transition: "transform 0.2s", transform: open ? "rotate(180deg)" : "none" }}>▼</div>
                </div>
            </button>

            {/* Детали */}
            {open && (
                <div style={{ background: "rgba(255,255,255,0.03)", padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
                    {/* Фичи */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                        {plan.features.map((f, i) => (
                            <div key={i} style={{ background: "rgba(255,255,255,0.06)", borderRadius: 14, padding: "10px 12px", fontSize: 13, fontWeight: 500, color: "var(--tg-theme-text-color, #e5e5e5)", display: "flex", alignItems: "center", gap: 6 }}>
                                <span>{f.icon}</span><span>{f.text}</span>
                            </div>
                        ))}
                    </div>

                    {/* Telegram Stars */}
                    <button
                        onClick={() => {
                            const tg = (window as any).Telegram?.WebApp;
                            if (tg) tg.close();
                            else alert("Открой бота → /premium → выбери Stars");
                        }}
                        style={{ width: "100%", padding: "14px 0", borderRadius: 18, background: "linear-gradient(135deg, #f59e0b, #fbbf24)", color: "#fff", fontWeight: 700, fontSize: 15, border: "none", cursor: "pointer", boxShadow: "0 6px 20px rgba(245,158,11,0.35)" }}
                    >
                        ⭐ Оплатить {plan.stars} Telegram Stars
                    </button>

                    {/* Разделитель */}
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
                        <span style={{ fontSize: 12, color: "var(--tg-theme-hint-color, #666)", whiteSpace: "nowrap" }}>или {plan.rub} ₽ через</span>
                        <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
                    </div>

                    {/* СБП и Крипто */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                        {/* СБП */}
                        <button
                            disabled={!!loading}
                            onClick={() => handlePay("sbp")}
                            style={{ padding: "14px 8px", borderRadius: 18, background: "linear-gradient(135deg, #059669, #10b981)", border: "none", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 4, opacity: loading ? 0.6 : 1, boxShadow: "0 4px 14px rgba(16,185,129,0.25)" }}
                        >
                            <span style={{ fontSize: 22 }}>{loading === "sbp" ? "⏳" : "📱"}</span>
                            <span style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>СБП</span>
                            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.7)" }}>Быстро</span>
                        </button>

                        {/* Крипто */}
                        <button
                            disabled={!!loading}
                            onClick={() => handlePay("crypto")}
                            style={{ padding: "14px 8px", borderRadius: 18, background: "linear-gradient(135deg, #7c3aed, #6366f1)", border: "none", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 4, opacity: loading ? 0.6 : 1, boxShadow: "0 4px 14px rgba(124,58,237,0.25)" }}
                        >
                            <span style={{ fontSize: 22 }}>{loading === "crypto" ? "⏳" : "₿"}</span>
                            <span style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>Крипто</span>
                            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.7)" }}>USDT</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Главная страница ──────────────────────────────────────────────────────────
export default function PremiumPage({ params }: { params: { users: string } }) {
    const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
    const [pollStatus, setPollStatus] = useState<"idle" | "polling" | "confirmed" | "failed">("idle");
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        if (!paymentData || pollStatus !== "polling") return;
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${BackEnd_URL}/api/v1/payments/platega/status/${paymentData.transaction_id}`);
                if (!res.ok) return;
                const d = await res.json();
                if (d.status === "CONFIRMED") { setPollStatus("confirmed"); clearInterval(pollRef.current!); }
                else if (d.status === "CANCELED") { setPollStatus("failed"); clearInterval(pollRef.current!); }
            } catch { /* ignore */ }
        }, 5000);
        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, [paymentData, pollStatus]);

    const startPayment = async (product: Product, method: Method) => {
        setPaymentData(null);
        setPollStatus("idle");
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/payments/platega/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ telegram_id: parseInt(params.users), product, method }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            const data: PaymentData = await res.json();
            setPaymentData(data);
            setPollStatus("polling");
        } catch (e: any) {
            alert(`Ошибка: ${e.message || "попробуй позже"}`);
        }
    };

    const reset = () => {
        setPaymentData(null);
        setPollStatus("idle");
        if (pollRef.current) clearInterval(pollRef.current);
    };

    if (pollStatus === "confirmed" && paymentData) {
        return <SuccessScreen product={paymentData.product} onClose={reset} />;
    }

    if (paymentData) {
        return <PaymentScreen data={paymentData} status={pollStatus} onBack={reset} userId={params.users} />;
    }

    return (
        <div style={{ minHeight: "100dvh", background: "var(--tg-theme-bg-color, #0f0f0f)", display: "flex", flexDirection: "column" }}>
            {/* Хедер */}
            <div style={{ background: "linear-gradient(135deg, #7c3aed 0%, #db2777 60%, #ef4444 100%)", padding: "calc(env(safe-area-inset-top) + 24px) 20px 28px", position: "relative", overflow: "hidden" }}>
                {/* Декоративные круги */}
                <div style={{ position: "absolute", top: -30, right: -30, width: 120, height: 120, borderRadius: "50%", background: "rgba(255,255,255,0.08)" }} />
                <div style={{ position: "absolute", bottom: -20, left: -10, width: 80, height: 80, borderRadius: "50%", background: "rgba(255,255,255,0.05)" }} />
                <div style={{ position: "relative", zIndex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.7)", marginBottom: 4, letterSpacing: "0.05em", textTransform: "uppercase" }}>LSJLove</div>
                    <div style={{ fontSize: 30, fontWeight: 900, color: "#fff", lineHeight: 1.1, marginBottom: 6 }}>Premium</div>
                    <div style={{ fontSize: 14, color: "rgba(255,255,255,0.75)" }}>Открой все возможности знакомств</div>
                </div>
            </div>

            {/* Планы */}
            <div style={{ padding: "16px 16px 24px", display: "flex", flexDirection: "column", gap: 12, flex: 1, overflowY: "auto" }}>
                {PLANS.map(plan => (
                    <PlanCard key={plan.id} plan={plan} onSelect={startPayment} />
                ))}

                {/* Безопасность */}
                <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 18, padding: "14px 16px", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6, color: "var(--tg-theme-text-color, #ccc)" }}>🔒 Безопасная оплата</div>
                    <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color, #777)", lineHeight: 1.6 }}>
                        СБП и Крипто (USDT) через Platega<br />
                        Telegram Stars — напрямую через Telegram
                    </div>
                </div>
            </div>

            <div style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 72px)" }} />
            <BottomNav userId={params.users} />
        </div>
    );
}
