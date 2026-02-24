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

const PRODUCTS = {
    premium: {
        name: "Premium", emoji: "⭐",
        stars: 500, rub: 299,
        color: "from-yellow-500 to-orange-500",
        features: ["Безлимитные лайки", "Кто тебя лайкнул", "Откат свайпа", "1 суперлайк/день"],
    },
    vip: {
        name: "VIP", emoji: "💎",
        stars: 1500, rub: 799,
        color: "from-purple-500 to-pink-500",
        features: ["Всё из Premium", "AI Icebreaker x10/день", "Буст профиля x3/нед", "Приоритет в поиске"],
    },
    superlike: {
        name: "Суперлайк", emoji: "💫",
        stars: 50, rub: 49,
        color: "from-blue-500 to-cyan-500",
        features: ["Профиль покажут первым", "Получатель увидит уведомление"],
    },
};

export default function PremiumPage({ params }: { params: { users: string } }) {
    const [selected, setSelected] = useState<Product | null>(null);
    const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
    const [loading, setLoading] = useState(false);
    const [pollStatus, setPollStatus] = useState<"idle" | "polling" | "confirmed" | "failed">("idle");
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Поллинг статуса транзакции
    useEffect(() => {
        if (!paymentData || pollStatus !== "polling") return;

        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(
                    `${BackEnd_URL}/api/v1/payments/platega/status/${paymentData.transaction_id}`
                );
                const d = await res.json();
                if (d.status === "CONFIRMED") {
                    setPollStatus("confirmed");
                    clearInterval(pollRef.current!);
                } else if (d.status === "CANCELED") {
                    setPollStatus("failed");
                    clearInterval(pollRef.current!);
                }
            } catch { /* ignore */ }
        }, 4000);

        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, [paymentData, pollStatus]);

    const startPayment = async (product: Product, method: Method) => {
        setLoading(true);
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

            // Для карты — сразу открываем redirect
            if (method === "card" && data.redirect_url) {
                window.open(data.redirect_url, "_blank");
            }
        } catch {
            alert("Ошибка создания платежа. Попробуй позже.");
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        const tg = (window as any).Telegram?.WebApp;
        if (tg) tg.showAlert("Скопировано!");
        else alert("Скопировано!");
    };

    const reset = () => {
        setPaymentData(null);
        setPollStatus("idle");
        if (pollRef.current) clearInterval(pollRef.current);
    };

    // ── Экран успешной оплаты ────────────────────────────────────────────────
    if (pollStatus === "confirmed") {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-6 px-8 text-center pb-20">
                <div className="text-7xl">🎉</div>
                <h2 className="text-2xl font-bold">Оплата прошла!</h2>
                <p className="text-default-500">
                    {paymentData?.product === "premium" ? "⭐ Premium" :
                     paymentData?.product === "vip" ? "💎 VIP" : "💫 Суперлайк"} активирован на 30 дней.
                </p>
                <button
                    onClick={reset}
                    className="mt-4 px-6 py-3 rounded-2xl bg-primary text-white font-semibold"
                >
                    ✓ Отлично!
                </button>
                <BottomNav userId={params.users} />
            </div>
        );
    }

    // ── Экран оплаты (QR / крипто) ───────────────────────────────────────────
    if (paymentData) {
        return (
            <div className="flex flex-col min-h-screen pb-20">
                <div className="px-4 py-4 border-b border-divider flex items-center gap-3">
                    <button onClick={reset} className="text-default-400 text-xl">←</button>
                    <h1 className="text-lg font-bold">
                        {paymentData.method === "sbp"    ? "📱 Оплата СБП"      :
                         paymentData.method === "crypto" ? "₿ Оплата криптой"   : "💳 Оплата картой"}
                    </h1>
                </div>

                <div className="p-4 flex flex-col gap-4">
                    {/* Статус поллинга */}
                    {pollStatus === "polling" && (
                        <div className="bg-yellow-500/10 rounded-2xl p-3 text-center text-sm text-yellow-600">
                            ⏳ Ожидаем подтверждение оплаты...
                        </div>
                    )}

                    {/* СБП — QR код */}
                    {paymentData.method === "sbp" && paymentData.qr_data && (
                        <div className="bg-white rounded-3xl p-6 flex flex-col items-center gap-4">
                            <p className="text-sm text-gray-500 text-center font-medium">
                                Отсканируй QR-код в приложении банка
                            </p>
                            <div className="p-2 bg-white rounded-xl shadow-sm">
                                <QRCode
                                    value={paymentData.qr_data}
                                    size={220}
                                    bgColor="#ffffff"
                                    fgColor="#000000"
                                />
                            </div>
                            <p className="text-xs text-gray-400 text-center">
                                Сумма: <b>{paymentData.amount} ₽</b>
                            </p>
                            {paymentData.expires_in && (
                                <p className="text-xs text-orange-500">
                                    ⏱ Действует: {paymentData.expires_in}
                                </p>
                            )}
                            {/* Кнопка открыть в браузере (fallback) */}
                            {paymentData.redirect_url && (
                                <a
                                    href={paymentData.redirect_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-primary underline"
                                >
                                    Открыть страницу оплаты →
                                </a>
                            )}
                        </div>
                    )}

                    {/* Крипто — адрес кошелька */}
                    {paymentData.method === "crypto" && (
                        <div className="bg-content1 rounded-3xl p-5 flex flex-col gap-4">
                            <p className="text-sm font-semibold text-center">
                                Переведи USDT на адрес кошелька:
                            </p>

                            {paymentData.wallet_address ? (
                                <>
                                    {/* QR кошелька */}
                                    <div className="flex justify-center bg-white rounded-2xl p-4">
                                        <QRCode
                                            value={paymentData.wallet_address}
                                            size={180}
                                            bgColor="#ffffff"
                                            fgColor="#000000"
                                        />
                                    </div>

                                    {/* Адрес */}
                                    <div className="bg-content2 rounded-xl p-3">
                                        <p className="text-xs text-default-400 mb-1">Адрес (TRC-20 / USDT):</p>
                                        <p className="text-sm font-mono break-all">{paymentData.wallet_address}</p>
                                        <button
                                            onClick={() => copyToClipboard(paymentData.wallet_address!)}
                                            className="mt-2 w-full py-1.5 rounded-lg bg-primary text-white text-xs font-medium"
                                        >
                                            📋 Скопировать адрес
                                        </button>
                                    </div>

                                    {/* Сумма в USDT */}
                                    {paymentData.usdt_amount && (
                                        <div className="bg-content2 rounded-xl p-3">
                                            <p className="text-xs text-default-400 mb-1">Сумма к оплате:</p>
                                            <p className="text-lg font-bold text-primary">
                                                {paymentData.usdt_amount} USDT
                                            </p>
                                            <p className="text-xs text-default-400">
                                                ≈ {paymentData.amount} ₽
                                                {paymentData.usdt_rate && ` (курс: 1 USDT = ${paymentData.usdt_rate} ₽)`}
                                            </p>
                                            <button
                                                onClick={() => copyToClipboard(String(paymentData.usdt_amount))}
                                                className="mt-2 w-full py-1.5 rounded-lg bg-content3 text-default-700 text-xs font-medium"
                                            >
                                                📋 Скопировать сумму
                                            </button>
                                        </div>
                                    )}
                                </>
                            ) : (
                                /* Если адрес не вернули — fallback редирект */
                                paymentData.redirect_url && (
                                    <a
                                        href={paymentData.redirect_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="w-full py-3 rounded-2xl bg-primary text-white font-semibold text-center block"
                                    >
                                        Открыть страницу оплаты крипто →
                                    </a>
                                )
                            )}

                            {paymentData.expires_in && (
                                <p className="text-xs text-orange-500 text-center">
                                    ⏱ Действует: {paymentData.expires_in}
                                </p>
                            )}
                        </div>
                    )}

                    {/* Карта — только кнопка редиректа */}
                    {paymentData.method === "card" && paymentData.redirect_url && (
                        <div className="bg-content1 rounded-3xl p-5 flex flex-col gap-3 text-center">
                            <p className="text-default-500 text-sm">
                                Страница оплаты открыта в браузере. Если не открылась — нажми кнопку:
                            </p>
                            <a
                                href={paymentData.redirect_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="w-full py-3 rounded-2xl bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold"
                            >
                                💳 Открыть страницу оплаты
                            </a>
                        </div>
                    )}

                    <button
                        onClick={reset}
                        className="w-full py-2.5 rounded-2xl bg-content2 text-default-500 text-sm"
                    >
                        ← Назад
                    </button>
                </div>

                <BottomNav userId={params.users} />
            </div>
        );
    }

    // ── Главный экран выбора тарифа ──────────────────────────────────────────
    return (
        <div className="flex flex-col min-h-screen pb-20">
            <div className="px-4 py-4 border-b border-divider">
                <h1 className="text-xl font-bold">⭐ Premium</h1>
                <p className="text-sm text-default-400 mt-1">Открой все возможности LSJLove</p>
            </div>

            <div className="p-4 flex flex-col gap-4">
                {(Object.entries(PRODUCTS) as [Product, typeof PRODUCTS[Product]][]).map(([id, p]) => (
                    <div key={id} className="rounded-2xl overflow-hidden shadow-md">
                        {/* Шапка */}
                        <div
                            className={`bg-gradient-to-r ${p.color} p-4 text-white cursor-pointer`}
                            onClick={() => setSelected(selected === id ? null : id)}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-lg font-bold">{p.emoji} {p.name}</p>
                                    <p className="text-sm opacity-90">
                                        {p.stars} Stars &nbsp;|&nbsp; {p.rub} ₽
                                    </p>
                                </div>
                                <span>{selected === id ? "▲" : "▼"}</span>
                            </div>
                        </div>

                        {selected === id && (
                            <div className="bg-content1 p-4 flex flex-col gap-3">
                                <ul className="text-sm text-default-600 space-y-1">
                                    {p.features.map((f) => <li key={f}>✅ {f}</li>)}
                                </ul>

                                {/* Telegram Stars */}
                                <button
                                    onClick={() => {
                                        const tg = (window as any).Telegram?.WebApp;
                                        tg?.close();
                                        alert("Открой бота и нажми /premium → выбери Stars");
                                    }}
                                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-yellow-600 text-white font-semibold text-sm"
                                >
                                    ⭐ {p.stars} Telegram Stars
                                </button>

                                <div className="flex items-center gap-2">
                                    <div className="flex-1 h-px bg-divider" />
                                    <span className="text-xs text-default-400">или оплати рублями</span>
                                    <div className="flex-1 h-px bg-divider" />
                                </div>

                                {/* Platega методы */}
                                <div className="grid grid-cols-3 gap-2">
                                    {[
                                        { id: "card"   as Method, icon: "💳", label: "Карта" },
                                        { id: "sbp"    as Method, icon: "📱", label: "СБП QR" },
                                        { id: "crypto" as Method, icon: "₿",  label: "Крипто" },
                                    ].map((m) => (
                                        <button
                                            key={m.id}
                                            disabled={loading}
                                            onClick={() => startPayment(id, m.id)}
                                            className="flex flex-col items-center py-3 rounded-xl bg-content2 hover:bg-content3 transition-colors disabled:opacity-60"
                                        >
                                            <span className="text-2xl">{m.icon}</span>
                                            <span className="text-xs mt-1">{m.label}</span>
                                            <span className="text-xs font-bold text-primary">{p.rub} ₽</span>
                                        </button>
                                    ))}
                                </div>

                                {loading && (
                                    <p className="text-center text-xs text-default-400">
                                        ⏳ Создаём платёж...
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                <div className="bg-content1 rounded-2xl p-4 text-xs text-default-400 text-center space-y-1">
                    <p>🔒 Платежи защищены · Платёжная система Platega</p>
                    <p>СБП: оплата QR-кодом за 10 сек · Крипто: USDT TRC-20</p>
                </div>
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}
