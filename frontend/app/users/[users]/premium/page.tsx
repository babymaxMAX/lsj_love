"use client";
import { useState } from "react";
import { BottomNav } from "@/components/bottom-nav";
import { BackEnd_URL } from "@/config/url";

type Product = "premium" | "vip" | "superlike";
type Method = "card" | "sbp" | "crypto";

const PRODUCTS = {
    premium: {
        name: "Premium",
        emoji: "⭐",
        stars: 500,
        rub: 299,
        features: ["Безлимитные лайки", "Кто тебя лайкнул", "Откат свайпа", "1 суперлайк/день"],
        color: "from-yellow-500 to-orange-500",
    },
    vip: {
        name: "VIP",
        emoji: "💎",
        stars: 1500,
        rub: 799,
        features: ["Всё из Premium", "AI Icebreaker x10/день", "Буст профиля x3/нед", "Приоритет в выдаче"],
        color: "from-purple-500 to-pink-500",
    },
    superlike: {
        name: "Суперлайк",
        emoji: "💫",
        stars: 50,
        rub: 49,
        features: ["Твой профиль покажут первым", "Пользователь увидит уведомление"],
        color: "from-blue-500 to-cyan-500",
    },
};

const METHODS: { id: Method; label: string; icon: string }[] = [
    { id: "card", label: "Карта (RUB)", icon: "💳" },
    { id: "sbp",  label: "СБП",         icon: "📱" },
    { id: "crypto", label: "Крипто",    icon: "₿" },
];

export default function PremiumPage({ params }: { params: { users: string } }) {
    const [selected, setSelected] = useState<Product | null>(null);
    const [loading, setLoading] = useState(false);
    const [paymentUrl, setPaymentUrl] = useState<string | null>(null);

    const handlePlategaPay = async (product: Product, method: Method) => {
        setLoading(true);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/payments/platega/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    telegram_id: parseInt(params.users),
                    product,
                    method,
                }),
            });
            const data = await res.json();
            if (data.payment_url) {
                setPaymentUrl(data.payment_url);
                // Открываем ссылку на оплату
                window.open(data.payment_url, "_blank");
            }
        } catch {
            alert("Ошибка создания платежа. Попробуй позже.");
        } finally {
            setLoading(false);
        }
    };

    const handleStarsPay = (product: Product) => {
        // Telegram Stars оплачиваются через бота
        const tg = (window as any).Telegram?.WebApp;
        tg?.close();
        alert("Открой бота и нажми /premium для оплаты через Telegram Stars");
    };

    return (
        <div className="flex flex-col min-h-screen pb-20">
            {/* Заголовок */}
            <div className="px-4 py-4 border-b border-divider">
                <h1 className="text-xl font-bold">⭐ Premium</h1>
                <p className="text-sm text-default-400 mt-1">Открой все возможности LSJLove</p>
            </div>

            <div className="p-4 flex flex-col gap-4">
                {/* Карточки продуктов */}
                {(Object.entries(PRODUCTS) as [Product, typeof PRODUCTS[Product]][]).map(([id, p]) => (
                    <div
                        key={id}
                        onClick={() => setSelected(selected === id ? null : id)}
                        className={`rounded-2xl overflow-hidden cursor-pointer transition-all shadow-md ${
                            selected === id ? "ring-2 ring-primary" : ""
                        }`}
                    >
                        {/* Шапка карточки */}
                        <div className={`bg-gradient-to-r ${p.color} p-4 text-white`}>
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-lg font-bold">{p.emoji} {p.name}</p>
                                    <p className="text-sm opacity-90">
                                        {p.stars} Stars &nbsp;|&nbsp; {p.rub} ₽
                                    </p>
                                </div>
                                <span className="text-2xl">{selected === id ? "▲" : "▼"}</span>
                            </div>
                        </div>

                        {/* Раскрытые детали */}
                        {selected === id && (
                            <div className="bg-content1 p-4">
                                <ul className="text-sm text-default-600 mb-4 space-y-1">
                                    {p.features.map((f) => (
                                        <li key={f}>✅ {f}</li>
                                    ))}
                                </ul>

                                {/* Telegram Stars */}
                                <button
                                    onClick={() => handleStarsPay(id)}
                                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-yellow-400 to-yellow-600 text-white font-semibold text-sm mb-2"
                                >
                                    ⭐ Оплатить {p.stars} Telegram Stars
                                </button>

                                {/* Разделитель */}
                                <div className="flex items-center gap-2 my-3">
                                    <div className="flex-1 h-px bg-divider" />
                                    <span className="text-xs text-default-400">или</span>
                                    <div className="flex-1 h-px bg-divider" />
                                </div>

                                {/* Platega способы */}
                                <p className="text-xs text-default-400 mb-2 text-center">
                                    Оплата картой / СБП / криптой — {p.rub} ₽
                                </p>
                                <div className="grid grid-cols-3 gap-2">
                                    {METHODS.map((m) => (
                                        <button
                                            key={m.id}
                                            disabled={loading}
                                            onClick={() => handlePlategaPay(id, m.id)}
                                            className="flex flex-col items-center py-2.5 rounded-xl bg-content2 hover:bg-content3 transition-colors text-sm font-medium disabled:opacity-60"
                                        >
                                            <span className="text-xl mb-1">{m.icon}</span>
                                            <span className="text-xs">{m.label}</span>
                                        </button>
                                    ))}
                                </div>

                                {loading && (
                                    <p className="text-center text-xs text-default-400 mt-2">
                                        ⏳ Создаём ссылку для оплаты...
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                {/* Инфо */}
                <div className="bg-content1 rounded-2xl p-4 text-xs text-default-400 text-center space-y-1">
                    <p>🔒 Все платежи защищены</p>
                    <p>Platega: карта, СБП, крипто — моментальная активация</p>
                    <p>Telegram Stars — через бота командой /premium</p>
                </div>
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}
