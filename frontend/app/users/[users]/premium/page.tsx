"use client";
import { BottomNav } from "@/components/bottom-nav";

const PLANS = [
    {
        id: "free",
        name: "Бесплатно",
        price: "0",
        color: "from-gray-500 to-gray-600",
        features: [
            "10 лайков в день",
            "Базовый поиск по городу",
            "1 AI Icebreaker в день",
        ],
        disabled: true,
        label: "Текущий план",
    },
    {
        id: "premium",
        name: "Premium",
        price: "500 Stars",
        color: "from-pink-500 to-rose-500",
        features: [
            "Безлимитные лайки",
            "Кто тебя лайкнул",
            "Откат последнего свайпа",
            "1 Суперлайк в день",
            "5 AI Icebreaker в день",
        ],
        disabled: false,
        label: "Получить Premium",
        payload: "premium_monthly",
    },
    {
        id: "vip",
        name: "VIP 💎",
        price: "1500 Stars",
        color: "from-purple-500 to-indigo-500",
        features: [
            "Всё из Premium",
            "10 AI Icebreaker в день",
            "Буст профиля 3 раза в неделю",
            "Приоритет в выдаче",
            "AI анализ профиля",
            "Верификация аккаунта ✓",
        ],
        disabled: false,
        label: "Получить VIP",
        payload: "vip_monthly",
    },
];

const MICROTX = [
    { icon: "⭐", name: "Суперлайк", price: "50 Stars", desc: "Твой профиль будет первым", payload: "superlike_single" },
    { icon: "🚀", name: "Буст профиля", price: "150 Stars", desc: "Попади в топ на 24 часа", payload: "boost_single" },
    { icon: "🤖", name: "Пакет AI (10 штук)", price: "200 Stars", desc: "10 AI Icebreaker сообщений", payload: "ai_pack" },
];

export default function PremiumPage({ params }: { params: { users: string } }) {
    const handleBuy = (payload: string) => {
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.showAlert(
                "Чтобы оплатить, напиши боту /premium и выбери нужный план. Оплата через Telegram Stars."
            );
        }
    };

    return (
        <div className="flex flex-col min-h-screen pb-20">
            {/* Заголовок */}
            <div className="px-4 py-6 text-center bg-gradient-to-b from-purple-500/10 to-transparent">
                <div className="text-4xl mb-2">⭐</div>
                <h1 className="text-2xl font-bold">LSJLove Premium</h1>
                <p className="text-default-500 text-sm mt-1">Найди своего человека быстрее</p>
            </div>

            {/* Планы */}
            <div className="px-4 space-y-4">
                {PLANS.map((plan) => (
                    <div
                        key={plan.id}
                        className="rounded-2xl border border-divider overflow-hidden bg-content1"
                    >
                        <div className={`bg-gradient-to-r ${plan.color} p-4`}>
                            <div className="flex justify-between items-center">
                                <h2 className="text-white font-bold text-lg">{plan.name}</h2>
                                <span className="text-white font-semibold">{plan.price}/мес</span>
                            </div>
                        </div>
                        <div className="p-4">
                            <ul className="space-y-2 mb-4">
                                {plan.features.map((f) => (
                                    <li key={f} className="flex items-center gap-2 text-sm text-default-600">
                                        <span className="text-green-500">✓</span> {f}
                                    </li>
                                ))}
                            </ul>
                            <button
                                onClick={() => plan.payload && handleBuy(plan.payload)}
                                disabled={plan.disabled}
                                className={`w-full py-3 rounded-xl font-semibold text-sm transition-opacity ${
                                    plan.disabled
                                        ? "bg-default-200 text-default-400 cursor-not-allowed"
                                        : `bg-gradient-to-r ${plan.color} text-white hover:opacity-90`
                                }`}
                            >
                                {plan.label}
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Микротранзакции */}
            <div className="px-4 mt-6">
                <h3 className="font-semibold mb-3 text-default-700">Разовые покупки</h3>
                <div className="space-y-3">
                    {MICROTX.map((item) => (
                        <div
                            key={item.payload}
                            className="flex items-center justify-between bg-content1 rounded-2xl px-4 py-3 border border-divider"
                        >
                            <div className="flex items-center gap-3">
                                <span className="text-2xl">{item.icon}</span>
                                <div>
                                    <p className="font-medium text-sm">{item.name}</p>
                                    <p className="text-xs text-default-400">{item.desc}</p>
                                </div>
                            </div>
                            <button
                                onClick={() => handleBuy(item.payload)}
                                className="bg-primary text-white text-xs font-semibold px-3 py-2 rounded-xl hover:opacity-90 transition-opacity whitespace-nowrap"
                            >
                                {item.price}
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            <div className="px-4 py-4 text-center text-xs text-default-400">
                Оплата через Telegram Stars — безопасно, без комиссии 🔒
            </div>

            <BottomNav userId={params.users} />
        </div>
    );
}

declare global {
    interface Window {
        Telegram?: { WebApp: { showAlert: (msg: string) => void } };
    }
}
