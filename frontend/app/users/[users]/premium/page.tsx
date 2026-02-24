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
    usdt_rate?: number;    // RUB per USDT, e.g. 94.5
    usdt_amount?: number;  // e.g. 3.16
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
        features: [
            { icon: "❤️", title: "Безлимитные лайки", desc: "Лайкай всех без ограничений. Бесплатно — только 10 в день." },
            { icon: "👁", title: "Кто тебя лайкнул", desc: "Видишь список людей, которым ты понравился — ещё до взаимного матча." },
            { icon: "↩️", title: "Откат свайпа", desc: "Случайно пропустил интересного человека? Вернись и посмотри снова." },
            { icon: "💫", title: "1 Суперлайк в день", desc: "Твой профиль появится первым и человек получит уведомление." },
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
        features: [
            { icon: "✅", title: "Всё из Premium", desc: "Безлимитные лайки, просмотр кто лайкнул, откат и суперлайки." },
            {
                icon: "🤖",
                title: "AI Icebreaker ×10/день",
                desc: "ИИ изучает анкету человека и пишет первое сообщение за тебя — персонально, не шаблонно. Ты просто жмёшь «Отправить».",
            },
            { icon: "🚀", title: "Буст профиля ×3/нед", desc: "Твоя анкета показывается первой всем пользователям 3 раза в неделю." },
            { icon: "🏆", title: "Приоритет в поиске", desc: "VIP-анкеты показываются выше в ленте — тебя видят чаще." },
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
        features: [
            { icon: "🔝", title: "Твой профиль — первым", desc: "Появишься в самом начале ленты у выбранного пользователя." },
            { icon: "🔔", title: "Уведомление", desc: "Человек получает уведомление что ты им суперлайкнул." },
        ],
    },
];

function toUsdt(rub: number, rubPerUsdt: number | null): string | null {
    if (!rubPerUsdt || rubPerUsdt <= 0) return null;
    return (rub / rubPerUsdt).toFixed(2);
}

// ── Экран успеха ─────────────────────────────────────────────────────────────
function SuccessScreen({ product, onClose }: { product: string; onClose: () => void }) {
    const p = PLANS.find(x => x.id === product);
    return (
        <div style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 24px 80px", textAlign: "center", background: "var(--tg-theme-bg-color, #0f0f0f)" }}>
            <div style={{ fontSize: 72, marginBottom: 24 }}>🎉</div>
            <h2 style={{ fontSize: 26, fontWeight: 900, marginBottom: 10, color: "var(--tg-theme-text-color, #fff)" }}>Оплата прошла!</h2>
            <p style={{ color: "var(--tg-theme-hint-color, #999)", marginBottom: 32, fontSize: 16 }}>
                {p ? `${p.emoji} ${p.name}` : product} активирован{product === "superlike" ? "" : " на 30 дней"}
            </p>
            <button onClick={onClose} style={{ padding: "14px 40px", borderRadius: 20, background: "linear-gradient(135deg, #7c3aed, #db2777)", color: "#fff", fontWeight: 700, fontSize: 16, border: "none", cursor: "pointer" }}>
                Отлично ✓
            </button>
        </div>
    );
}

// ── Экран оплаты ─────────────────────────────────────────────────────────────
function PaymentScreen({ data, status, onBack, userId }: {
    data: PaymentData; status: string; onBack: () => void; userId: string;
}) {
    const openPayment = () => {
        if (!data.redirect_url) return;
        const tg = (window as any).Telegram?.WebApp;
        if (tg?.openLink) tg.openLink(data.redirect_url);
        else window.open(data.redirect_url, "_blank");
    };

    const p = PLANS.find(x => x.id === data.product);
    const isCrypto = data.method === "crypto";

    return (
        <div style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", background: "var(--tg-theme-bg-color, #0f0f0f)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "calc(env(safe-area-inset-top) + 14px) 16px 14px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                <button onClick={onBack} style={{ width: 36, height: 36, borderRadius: 12, background: "rgba(255,255,255,0.08)", border: "none", color: "#fff", fontSize: 18, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>←</button>
                <span style={{ fontWeight: 700, fontSize: 17, color: "var(--tg-theme-text-color, #fff)" }}>
                    {isCrypto ? "₿ Оплата USDT" : "📱 Оплата через СБП"}
                </span>
            </div>

            <div style={{ padding: "16px 16px 24px", display: "flex", flexDirection: "column", gap: 14, flex: 1, overflowY: "auto" }}>

                {/* Блок суммы */}
                <div style={{ background: isCrypto ? "linear-gradient(135deg, rgba(249,115,22,0.15), rgba(234,179,8,0.1))" : "rgba(255,255,255,0.05)", borderRadius: 20, padding: "20px", border: `1px solid ${isCrypto ? "rgba(249,115,22,0.3)" : "rgba(255,255,255,0.07)"}` }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: isCrypto && data.usdt_amount ? 14 : 0 }}>
                        <div>
                            <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color, #888)", marginBottom: 4 }}>Тариф</div>
                            <div style={{ fontWeight: 700, fontSize: 16, color: "var(--tg-theme-text-color, #fff)" }}>
                                {p ? `${p.emoji} ${p.name}` : data.product}
                            </div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: 22, fontWeight: 900, color: "#fff" }}>{data.amount} ₽</div>
                        </div>
                    </div>

                    {/* USDT сумма — крупно */}
                    {isCrypto && data.usdt_amount && (
                        <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: 16, padding: "16px 18px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <div>
                                <div style={{ fontSize: 12, color: "#f97316", fontWeight: 700, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                                    К переводу
                                </div>
                                <div style={{ fontSize: 36, fontWeight: 900, color: "#fff", lineHeight: 1 }}>
                                    {data.usdt_amount}
                                </div>
                                <div style={{ fontSize: 16, fontWeight: 700, color: "#f97316", marginTop: 2 }}>USDT</div>
                                {data.usdt_rate && (
                                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", marginTop: 6 }}>
                                        курс: 1 USDT = {data.usdt_rate} ₽
                                    </div>
                                )}
                            </div>
                            <div style={{ fontSize: 48, opacity: 0.6 }}>₿</div>
                        </div>
                    )}
                </div>

                {/* Статус */}
                {status === "polling" && (
                    <div style={{ background: "rgba(234,179,8,0.08)", border: "1px solid rgba(234,179,8,0.2)", borderRadius: 16, padding: "12px 16px", display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={{ fontSize: 20 }}>⏳</span>
                        <div>
                            <div style={{ fontWeight: 600, fontSize: 14, color: "#eab308" }}>Ожидаем оплату...</div>
                            <div style={{ fontSize: 12, color: "rgba(234,179,8,0.5)" }}>Проверяем каждые 5 секунд</div>
                        </div>
                    </div>
                )}

                {/* Инструкция */}
                <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 20, padding: "18px 20px", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, color: "var(--tg-theme-text-color, #fff)" }}>
                        {isCrypto ? "Как перевести USDT:" : "Как оплатить через СБП:"}
                    </div>
                    {(isCrypto
                        ? [
                            "Нажми кнопку «Открыть страницу оплаты»",
                            "На странице выбери Валюта → USDT, Сеть → TRC-20",
                            `Переведи ровно ${data.usdt_amount ? data.usdt_amount + " USDT" : "указанную сумму"} на адрес кошелька`,
                            "Перевод подтверждается автоматически (~5 мин)",
                          ]
                        : [
                            "Нажми «Открыть СБП» ниже",
                            "Выбери свой банк на странице",
                            "Подтверди перевод в приложении банка",
                          ]
                    ).map((step, i) => (
                        <div key={i} style={{ display: "flex", gap: 12, marginBottom: i < (isCrypto ? 3 : 2) ? 12 : 0, alignItems: "flex-start" }}>
                            <div style={{
                                minWidth: 26, height: 26, borderRadius: "50%",
                                background: isCrypto ? "rgba(249,115,22,0.15)" : "rgba(5,150,105,0.15)",
                                border: `1px solid ${isCrypto ? "rgba(249,115,22,0.35)" : "rgba(5,150,105,0.35)"}`,
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: 12, fontWeight: 700,
                                color: isCrypto ? "#f97316" : "#10b981",
                                flexShrink: 0,
                            }}>
                                {i + 1}
                            </div>
                            <div style={{ fontSize: 14, color: "var(--tg-theme-text-color, #ccc)", paddingTop: 3, lineHeight: 1.4 }}>{step}</div>
                        </div>
                    ))}
                </div>

                {data.expires_in && (
                    <div style={{ textAlign: "center", fontSize: 13, color: "#f97316" }}>
                        ⏱ Платёж действителен: <b>{data.expires_in}</b>
                    </div>
                )}

                {isCrypto && (
                    <div style={{ background: "rgba(249,115,22,0.08)", borderRadius: 14, padding: "10px 14px", border: "1px solid rgba(249,115,22,0.2)", fontSize: 13, color: "#f97316", lineHeight: 1.5 }}>
                        💡 На странице оплаты: выбери <b>USDT</b> и сеть <b>TRC-20</b>, затем «Перейти к оплате»
                    </div>
                )}

                {data.redirect_url && (
                    <button onClick={openPayment} style={{
                        width: "100%", padding: "16px 0", borderRadius: 20,
                        background: isCrypto ? "linear-gradient(135deg, #f97316, #eab308)" : "linear-gradient(135deg, #059669, #10b981)",
                        color: "#fff", fontWeight: 800, fontSize: 16, border: "none", cursor: "pointer",
                        boxShadow: isCrypto ? "0 8px 24px rgba(249,115,22,0.3)" : "0 8px 24px rgba(16,185,129,0.3)",
                    }}>
                        {isCrypto ? "₿ Открыть страницу оплаты" : "📱 Открыть СБП"}
                    </button>
                )}

                <button onClick={onBack} style={{ width: "100%", padding: "13px 0", borderRadius: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", color: "var(--tg-theme-hint-color, #888)", fontWeight: 600, fontSize: 14, cursor: "pointer" }}>
                    ← Назад
                </button>
            </div>

            <div style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 80px)" }} />
            <BottomNav userId={userId} />
        </div>
    );
}

// ── Карточка плана ─────────────────────────────────────────────────────────────
function PlanCard({ plan, rubPerUsdt, onPay }: {
    plan: typeof PLANS[0];
    rubPerUsdt: number | null;
    onPay: (p: Product, m: Method) => Promise<void>;
}) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState<string | null>(null);
    const usdtPrice = toUsdt(plan.rub, rubPerUsdt);

    const handlePay = async (method: Method) => {
        setLoading(method);
        await onPay(plan.id, method);
        setLoading(null);
    };

    return (
        <div style={{ borderRadius: 24, overflow: "hidden", border: open ? "1.5px solid rgba(255,255,255,0.18)" : "1.5px solid rgba(255,255,255,0.06)", transition: "border-color 0.2s" }}>
            {/* Шапка */}
            <button
                onClick={() => setOpen(!open)}
                style={{ width: "100%", background: plan.gradient, padding: "18px 20px", border: "none", cursor: "pointer", textAlign: "left", display: "block" }}
            >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                    <div>
                        {plan.badge && (
                            <div style={{ display: "inline-block", background: "rgba(0,0,0,0.25)", borderRadius: 100, padding: "3px 10px", fontSize: 11, fontWeight: 700, color: "#fff", marginBottom: 8 }}>
                                {plan.badge}
                            </div>
                        )}
                        <div style={{ fontSize: 26, fontWeight: 900, color: "#fff", marginBottom: 4 }}>
                            {plan.emoji} {plan.name}
                        </div>
                        <div style={{ display: "flex", alignItems: "baseline", flexWrap: "wrap", gap: "4px 8px" }}>
                            <span style={{ fontSize: 24, fontWeight: 800, color: "#fff" }}>{plan.rub} ₽</span>
                            <span style={{ fontSize: 13, color: "rgba(255,255,255,0.7)" }}>{plan.period}</span>
                            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.45)" }}>· {plan.stars} ⭐</span>
                            {usdtPrice && (
                                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", background: "rgba(0,0,0,0.2)", borderRadius: 6, padding: "1px 6px" }}>
                                    ≈ {usdtPrice} USDT
                                </span>
                            )}
                        </div>
                    </div>
                    <div style={{ fontSize: 18, color: "rgba(255,255,255,0.75)", marginTop: 4, transition: "transform 0.2s", transform: open ? "rotate(180deg)" : "none" }}>▼</div>
                </div>
            </button>

            {/* Детали */}
            {open && (
                <div style={{ background: "rgba(255,255,255,0.025)", padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
                    {/* Фичи */}
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {plan.features.map((f, i) => (
                            <div key={i} style={{ background: "rgba(255,255,255,0.05)", borderRadius: 16, padding: "12px 14px", display: "flex", gap: 12, alignItems: "flex-start", border: "1px solid rgba(255,255,255,0.06)" }}>
                                <span style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>{f.icon}</span>
                                <div>
                                    <div style={{ fontWeight: 700, fontSize: 14, color: "var(--tg-theme-text-color, #e5e5e5)", marginBottom: 3 }}>{f.title}</div>
                                    <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color, #888)", lineHeight: 1.45 }}>{f.desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Telegram Stars */}
                    <button
                        onClick={() => {
                            const tg = (window as any).Telegram?.WebApp;
                            if (tg) tg.close();
                            else alert("Открой бота → /premium → выбери Telegram Stars");
                        }}
                        style={{ width: "100%", padding: "14px 0", borderRadius: 18, background: "linear-gradient(135deg, #f59e0b, #fbbf24)", color: "#fff", fontWeight: 800, fontSize: 15, border: "none", cursor: "pointer", boxShadow: "0 6px 20px rgba(245,158,11,0.35)", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
                    >
                        ⭐ Оплатить {plan.stars} Telegram Stars
                    </button>

                    {/* Разделитель */}
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
                        <span style={{ fontSize: 12, color: "var(--tg-theme-hint-color, #666)", whiteSpace: "nowrap" }}>или через</span>
                        <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
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
                            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>{plan.rub} ₽</span>
                        </button>

                        {/* Крипто */}
                        <button
                            disabled={!!loading}
                            onClick={() => handlePay("crypto")}
                            style={{ padding: "14px 8px", borderRadius: 18, background: "linear-gradient(135deg, #92400e, #f97316)", border: "none", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 4, opacity: loading ? 0.6 : 1, boxShadow: "0 4px 14px rgba(249,115,22,0.25)" }}
                        >
                            <span style={{ fontSize: 22 }}>{loading === "crypto" ? "⏳" : "₿"}</span>
                            <span style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>USDT</span>
                            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>
                                {usdtPrice ? `≈ ${usdtPrice}` : `${plan.rub} ₽`}
                            </span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Главная страница ──────────────────────────────────────────────────────────
export default function PremiumPage({ params }: { params: { users: string } }) {
    const [rubPerUsdt, setRubPerUsdt] = useState<number | null>(null);
    const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
    const [pollStatus, setPollStatus] = useState<"idle" | "polling" | "confirmed" | "failed">("idle");
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Загружаем курс USDT при открытии страницы
    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/payments/platega/usdt-rate`)
            .then(r => r.json())
            .then(d => {
                // d.rub_per_usdt = RUB за 1 USDT (например 94)
                if (d.rub_per_usdt && d.rub_per_usdt > 0) {
                    setRubPerUsdt(d.rub_per_usdt);
                }
            })
            .catch(() => {/* не критично */});
    }, []);

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
                throw new Error(err.detail || `Ошибка сервера ${res.status}`);
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
            <div style={{ background: "linear-gradient(135deg, #7c3aed 0%, #db2777 60%, #ef4444 100%)", padding: "calc(env(safe-area-inset-top) + 22px) 20px 26px", position: "relative", overflow: "hidden" }}>
                <div style={{ position: "absolute", top: -40, right: -20, width: 130, height: 130, borderRadius: "50%", background: "rgba(255,255,255,0.07)" }} />
                <div style={{ position: "absolute", bottom: -20, left: 20, width: 80, height: 80, borderRadius: "50%", background: "rgba(255,255,255,0.05)" }} />
                <div style={{ position: "relative", zIndex: 1 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.65)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>LSJLove</div>
                    <div style={{ fontSize: 28, fontWeight: 900, color: "#fff", lineHeight: 1.1, marginBottom: 6 }}>Premium</div>
                    <div style={{ fontSize: 14, color: "rgba(255,255,255,0.75)" }}>Открой все возможности знакомств</div>
                    {rubPerUsdt && (
                        <div style={{ marginTop: 8, fontSize: 12, color: "rgba(255,255,255,0.5)" }}>
                            Курс USDT: 1 USDT ≈ {rubPerUsdt} ₽
                        </div>
                    )}
                </div>
            </div>

            {/* Планы */}
            <div style={{ padding: "14px 14px 20px", display: "flex", flexDirection: "column", gap: 12, flex: 1, overflowY: "auto" }}>
                {PLANS.map(plan => (
                    <PlanCard key={plan.id} plan={plan} rubPerUsdt={rubPerUsdt} onPay={startPayment} />
                ))}

                <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: 16, padding: "12px 16px", border: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "flex-start", gap: 10 }}>
                    <span style={{ fontSize: 18 }}>🔒</span>
                    <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color, #666)", lineHeight: 1.5 }}>
                        <span style={{ fontWeight: 600, color: "var(--tg-theme-text-color, #999)" }}>Безопасная оплата</span><br />
                        СБП и Крипто (USDT TRC-20) через Platega · Stars через Telegram
                    </div>
                </div>
            </div>

            <div style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 72px)" }} />
            <BottomNav userId={params.users} />
        </div>
    );
}
