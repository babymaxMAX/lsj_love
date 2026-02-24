"use client";
import { useState, useEffect, useRef } from "react";
import QRCode from "react-qr-code";
import { BottomNav } from "@/components/bottom-nav";
import { BackEnd_URL } from "@/config/url";

type Product = "premium" | "vip" | "superlike";
type Method  = "card" | "sbp" | "crypto";

interface PaymentData {
    transaction_id: string;
    method: Method;
    product: string;
    amount: number;
    redirect_url?: string;
    qr_data?: string;
    wallet_address?: string;
    usdt_amount?: number;
    usdt_rate?: number;
    expires_in?: string;
}

const PLANS = [
    {
        id: "premium" as Product,
        name: "Premium",
        emoji: "⭐",
        stars: 500,
        rub: 299,
        period: "/ месяц",
        badge: "Популярный",
        badgeColor: "bg-yellow-500",
        gradient: "from-[#f59e0b] to-[#ef4444]",
        ring: "ring-yellow-500",
        features: [
            "❤️ Безлимитные лайки",
            "👁 Кто тебя лайкнул",
            "↩️ Откат свайпа",
            "💫 1 суперлайк в день",
        ],
    },
    {
        id: "vip" as Product,
        name: "VIP",
        emoji: "💎",
        stars: 1500,
        rub: 799,
        period: "/ месяц",
        badge: "Максимум",
        badgeColor: "bg-purple-600",
        gradient: "from-[#7c3aed] to-[#db2777]",
        ring: "ring-purple-500",
        features: [
            "✅ Всё из Premium",
            "🤖 AI Icebreaker × 10/день",
            "🚀 Буст профиля × 3/нед",
            "🏆 Приоритет в поиске",
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
        badgeColor: "",
        gradient: "from-[#0ea5e9] to-[#6366f1]",
        ring: "ring-blue-500",
        features: [
            "🔝 Твой профиль — первым",
            "🔔 Пользователь получит уведомление",
        ],
    },
];

const METHODS = [
    { id: "sbp"    as Method, icon: "📱", label: "СБП",    sub: "QR‑код" },
    { id: "card"   as Method, icon: "💳", label: "Карта",  sub: "RUB"    },
    { id: "crypto" as Method, icon: "₿",  label: "Крипто", sub: "USDT"   },
];

// ── Экран успеха ─────────────────────────────────────────────────────────────
function SuccessScreen({ product, onClose }: { product: string; onClose: () => void }) {
    const label = product === "premium" ? "⭐ Premium" : product === "vip" ? "💎 VIP" : "💫 Суперлайк";
    return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-6 px-8 text-center pb-24">
            <div className="w-24 h-24 rounded-full bg-green-500/20 flex items-center justify-center text-5xl animate-bounce">🎉</div>
            <div>
                <h2 className="text-2xl font-bold mb-2">Оплата прошла!</h2>
                <p className="text-default-400">{label} активирован{product === "superlike" ? "" : " на 30 дней"}.</p>
            </div>
            <button onClick={onClose} className="px-8 py-3 rounded-2xl bg-primary text-white font-bold text-base shadow-lg shadow-primary/30">
                Отлично! ✓
            </button>
        </div>
    );
}

// ── Экран оплаты ─────────────────────────────────────────────────────────────
function PaymentScreen({ data, status, onBack }: { data: PaymentData; status: string; onBack: () => void }) {
    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        const tg = (window as any).Telegram?.WebApp;
        if (tg) tg.showAlert("Скопировано!");
    };

    return (
        <div className="flex flex-col min-h-screen pb-24">
            {/* Хедер */}
            <div className="flex items-center gap-3 px-4 py-4 border-b border-white/10">
                <button onClick={onBack} className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center text-lg">←</button>
                <h1 className="font-bold text-lg">
                    {data.method === "sbp" ? "📱 Оплата СБП" : data.method === "crypto" ? "₿ Оплата криптой" : "💳 Оплата картой"}
                </h1>
            </div>

            <div className="p-4 flex flex-col gap-4">
                {/* Статус */}
                {status === "polling" && (
                    <div className="flex items-center gap-3 bg-yellow-500/10 border border-yellow-500/30 rounded-2xl px-4 py-3">
                        <span className="text-xl animate-spin">⏳</span>
                        <p className="text-sm text-yellow-400 font-medium">Ожидаем подтверждение...</p>
                    </div>
                )}

                {/* СБП — QR */}
                {data.method === "sbp" && data.qr_data && (
                    <div className="bg-white rounded-3xl p-6 flex flex-col items-center gap-4 shadow-xl">
                        <p className="text-gray-700 font-semibold text-sm">Отсканируй QR в приложении банка</p>
                        <div className="p-3 bg-white rounded-2xl border-4 border-gray-100 shadow-inner">
                            <QRCode value={data.qr_data} size={200} bgColor="#fff" fgColor="#0f172a" />
                        </div>
                        <div className="flex items-center justify-between w-full bg-gray-50 rounded-2xl px-4 py-3">
                            <span className="text-gray-500 text-sm">Сумма</span>
                            <span className="text-gray-900 font-bold text-lg">{data.amount} ₽</span>
                        </div>
                        {data.expires_in && (
                            <p className="text-xs text-orange-500">⏱ QR действует: {data.expires_in}</p>
                        )}
                        {data.redirect_url && (
                            <a href={data.redirect_url} target="_blank" rel="noreferrer"
                               className="text-xs text-blue-500 underline">
                                Открыть страницу оплаты →
                            </a>
                        )}
                    </div>
                )}

                {/* Крипто */}
                {data.method === "crypto" && (
                    <div className="flex flex-col gap-3">
                        {data.wallet_address ? (
                            <>
                                <div className="bg-content1 rounded-3xl p-5 flex flex-col items-center gap-4 shadow-sm">
                                    <p className="text-sm font-semibold">Адрес кошелька (TRC-20 / USDT)</p>
                                    <div className="bg-white p-4 rounded-2xl">
                                        <QRCode value={data.wallet_address} size={160} bgColor="#fff" fgColor="#0f172a" />
                                    </div>
                                    <div className="w-full bg-content2 rounded-2xl p-3">
                                        <p className="text-xs text-default-400 mb-1 font-medium">Адрес:</p>
                                        <p className="text-xs font-mono break-all text-default-700">{data.wallet_address}</p>
                                        <button onClick={() => copyToClipboard(data.wallet_address!)}
                                            className="mt-2 w-full py-2 rounded-xl bg-primary/10 text-primary text-xs font-bold">
                                            📋 Скопировать адрес
                                        </button>
                                    </div>
                                    {data.usdt_amount && (
                                        <div className="w-full bg-content2 rounded-2xl p-3">
                                            <p className="text-xs text-default-400 mb-1 font-medium">Сумма к переводу:</p>
                                            <p className="text-xl font-bold text-primary">{data.usdt_amount} USDT</p>
                                            <p className="text-xs text-default-400">
                                                ≈ {data.amount} ₽
                                                {data.usdt_rate ? ` · курс ${data.usdt_rate} ₽/USDT` : ""}
                                            </p>
                                            <button onClick={() => copyToClipboard(String(data.usdt_amount))}
                                                className="mt-2 w-full py-2 rounded-xl bg-content3 text-default-700 text-xs font-bold">
                                                📋 Скопировать сумму
                                            </button>
                                        </div>
                                    )}
                                </div>
                                {data.expires_in && (
                                    <p className="text-xs text-orange-400 text-center">⏱ Ждём перевод: {data.expires_in}</p>
                                )}
                            </>
                        ) : data.redirect_url ? (
                            <a href={data.redirect_url} target="_blank" rel="noreferrer"
                               className="block w-full py-4 rounded-2xl bg-gradient-to-r from-orange-500 to-yellow-500 text-white text-center font-bold shadow-lg">
                                ₿ Открыть страницу крипто-оплаты
                            </a>
                        ) : null}
                    </div>
                )}

                {/* Карта */}
                {data.method === "card" && data.redirect_url && (
                    <div className="bg-content1 rounded-3xl p-5 flex flex-col gap-4 text-center shadow-sm">
                        <div className="text-4xl">💳</div>
                        <p className="text-default-400 text-sm">Страница оплаты открыта. Если нет — нажми кнопку:</p>
                        <a href={data.redirect_url} target="_blank" rel="noreferrer"
                           className="block py-4 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-base shadow-lg shadow-blue-500/30">
                            Перейти к оплате картой →
                        </a>
                        <p className="text-xs text-default-400">Сумма: <b>{data.amount} ₽</b></p>
                    </div>
                )}

                <button onClick={onBack}
                    className="w-full py-3 rounded-2xl border border-white/10 text-default-400 text-sm font-medium">
                    ← Вернуться назад
                </button>
            </div>
            <BottomNav userId={data.transaction_id.split(":")[0] || "0"} />
        </div>
    );
}

// ── Главная страница ──────────────────────────────────────────────────────────
export default function PremiumPage({ params }: { params: { users: string } }) {
    const [selected, setSelected] = useState<Product | null>(null);
    const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
    const [loading, setLoading] = useState<string | null>(null); // "sbp_premium" etc
    const [pollStatus, setPollStatus] = useState<"idle" | "polling" | "confirmed" | "failed">("idle");
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        if (!paymentData || pollStatus !== "polling") return;
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${BackEnd_URL}/api/v1/payments/platega/status/${paymentData.transaction_id}`);
                const d = await res.json();
                if (d.status === "CONFIRMED") { setPollStatus("confirmed"); clearInterval(pollRef.current!); }
                else if (d.status === "CANCELED") { setPollStatus("failed"); clearInterval(pollRef.current!); }
            } catch { /* ignore */ }
        }, 4000);
        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, [paymentData, pollStatus]);

    const startPayment = async (product: Product, method: Method) => {
        const key = `${method}_${product}`;
        setLoading(key);
        setPaymentData(null);
        setPollStatus("idle");
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/payments/platega/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ telegram_id: parseInt(params.users), product, method }),
            });
            if (!res.ok) throw new Error("API error");
            const data: PaymentData = await res.json();
            setPaymentData(data);
            setPollStatus("polling");
            if (method === "card" && data.redirect_url) window.open(data.redirect_url, "_blank");
        } catch {
            alert("Ошибка создания платежа. Попробуй позже.");
        } finally {
            setLoading(null);
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
        return <PaymentScreen data={paymentData} status={pollStatus} onBack={reset} />;
    }

    return (
        <div className="flex flex-col min-h-screen pb-24">
            {/* Хедер */}
            <div className="relative overflow-hidden bg-gradient-to-br from-[#7c3aed] via-[#db2777] to-[#ef4444] px-6 py-8 text-white">
                <div className="absolute inset-0 opacity-20" style={{backgroundImage:"radial-gradient(circle at 20% 80%,#fff 1px,transparent 1px),radial-gradient(circle at 80% 20%,#fff 1px,transparent 1px)", backgroundSize:"40px 40px"}} />
                <h1 className="text-2xl font-black relative z-10">LSJLove Premium</h1>
                <p className="text-white/80 text-sm mt-1 relative z-10">Открой все возможности знакомств</p>
            </div>

            <div className="p-4 flex flex-col gap-3">
                {PLANS.map((plan) => {
                    const isOpen = selected === plan.id;
                    return (
                        <div key={plan.id}
                            className={`rounded-3xl overflow-hidden shadow-sm border transition-all duration-200 ${isOpen ? `border-transparent ring-2 ${plan.ring}` : "border-white/10"}`}>
                            {/* Шапка плана */}
                            <button
                                onClick={() => setSelected(isOpen ? null : plan.id)}
                                className={`w-full bg-gradient-to-r ${plan.gradient} p-5 text-white text-left`}
                            >
                                <div className="flex items-start justify-between">
                                    <div>
                                        {plan.badge && (
                                            <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${plan.badgeColor} text-white mb-2`}>
                                                {plan.badge}
                                            </span>
                                        )}
                                        <div className="flex items-baseline gap-2">
                                            <span className="text-3xl font-black">{plan.emoji} {plan.name}</span>
                                        </div>
                                        <div className="flex items-baseline gap-3 mt-1">
                                            <span className="text-2xl font-bold">{plan.rub} ₽</span>
                                            <span className="text-white/70 text-sm">{plan.period}</span>
                                            <span className="text-white/50 text-xs">· {plan.stars} Stars</span>
                                        </div>
                                    </div>
                                    <span className="text-2xl mt-1">{isOpen ? "▲" : "▼"}</span>
                                </div>
                            </button>

                            {/* Детали */}
                            {isOpen && (
                                <div className="bg-content1 p-4 flex flex-col gap-4">
                                    {/* Фичи */}
                                    <div className="grid grid-cols-2 gap-2">
                                        {plan.features.map(f => (
                                            <div key={f} className="bg-content2 rounded-2xl px-3 py-2 text-xs font-medium">{f}</div>
                                        ))}
                                    </div>

                                    {/* Stars */}
                                    <button
                                        onClick={() => {
                                            const tg = (window as any).Telegram?.WebApp;
                                            if (tg) { tg.close(); } else alert("Открой бота → /premium → выбери Stars");
                                        }}
                                        className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-amber-400 to-yellow-500 text-white font-bold text-sm shadow-md shadow-yellow-500/30 flex items-center justify-center gap-2"
                                    >
                                        ⭐ Оплатить {plan.stars} Telegram Stars
                                    </button>

                                    {/* Разделитель */}
                                    <div className="flex items-center gap-3">
                                        <div className="flex-1 h-px bg-white/10" />
                                        <span className="text-xs text-default-400 font-medium">или {plan.rub} ₽ через</span>
                                        <div className="flex-1 h-px bg-white/10" />
                                    </div>

                                    {/* Platega методы */}
                                    <div className="grid grid-cols-3 gap-2">
                                        {METHODS.map(m => {
                                            const key = `${m.id}_${plan.id}`;
                                            const isLoading = loading === key;
                                            return (
                                                <button
                                                    key={m.id}
                                                    disabled={!!loading}
                                                    onClick={() => startPayment(plan.id, m.id)}
                                                    className="flex flex-col items-center py-3.5 rounded-2xl bg-content2 active:scale-95 transition-transform disabled:opacity-50 gap-1 border border-white/5"
                                                >
                                                    <span className="text-2xl">{isLoading ? "⏳" : m.icon}</span>
                                                    <span className="text-xs font-semibold">{m.label}</span>
                                                    <span className="text-[10px] text-default-400">{m.sub}</span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}

                {/* Footer */}
                <div className="mt-2 rounded-2xl bg-content1 border border-white/5 p-4 flex flex-col gap-1.5 text-xs text-default-400 text-center">
                    <p className="font-semibold text-default-500">🔒 Безопасная оплата</p>
                    <p>СБП · Карта · Крипто (USDT) — через Platega</p>
                    <p>Telegram Stars — напрямую через Telegram</p>
                </div>
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}
