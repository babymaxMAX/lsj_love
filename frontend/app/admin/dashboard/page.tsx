"use client";
import { useEffect, useState } from "react";
import { BackEnd_URL } from "@/config/url";

interface Stats {
    users: {
        total: number; active: number; banned: number;
        online_5min: number; online_hour: number;
        new_today: number; new_week: number; new_month: number;
        male: number; female: number;
    };
    subscriptions: { premium: number; vip: number; free: number };
    activity: { total_likes: number; matches: number; likes_today: number };
}

function StatCard({ label, value, sub, color = "#7c3aed" }: {
    label: string; value: number | string; sub?: string; color?: string;
}) {
    return (
        <div style={{
            background: "#1a1a2e", borderRadius: 12, padding: "20px 24px",
            border: "1px solid rgba(255,255,255,0.08)",
        }}>
            <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, marginBottom: 8 }}>{label}</div>
            <div style={{ color: "#fff", fontSize: 28, fontWeight: 700, lineHeight: 1 }}>{value}</div>
            {sub && <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, marginTop: 6 }}>{sub}</div>}
        </div>
    );
}

export default function AdminDashboard() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const fetchStats = async () => {
        const key = localStorage.getItem("kupidon_admin_key") || "";
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/admin/stats`, {
                headers: { "X-Admin-Key": key },
            });
            if (!res.ok) { setError("Ошибка загрузки"); return; }
            setStats(await res.json());
        } catch {
            setError("Нет соединения");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchStats(); }, []);

    const s = { color: "#fff", padding: "24px 32px" };

    if (loading) return <div style={s}>Загрузка статистики...</div>;
    if (error || !stats) return <div style={{ ...s, color: "#f87171" }}>{error || "Ошибка"}</div>;

    return (
        <div style={{ padding: "32px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
                <h1 style={{ color: "#fff", fontSize: 24, fontWeight: 700, margin: 0 }}>📊 Статистика</h1>
                <button onClick={fetchStats} style={{
                    background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
                    color: "#fff", borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13,
                }}>
                    Обновить
                </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
                <StatCard label="Всего пользователей" value={stats.users.total} />
                <StatCard label="Активных анкет" value={stats.users.active} />
                <StatCard label="Онлайн (5 мин)" value={stats.users.online_5min} color="#10b981" />
                <StatCard label="Онлайн (час)" value={stats.users.online_hour} color="#10b981" />
                <StatCard label="Новых сегодня" value={stats.users.new_today} sub={`Неделя: ${stats.users.new_week} | Месяц: ${stats.users.new_month}`} />
                <StatCard label="Заблокированных" value={stats.users.banned} color="#ef4444" />
            </div>

            <h2 style={{ color: "rgba(255,255,255,0.7)", fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Пол</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 32 }}>
                <StatCard label="Мужчин" value={stats.users.male} color="#3b82f6" />
                <StatCard label="Женщин" value={stats.users.female} color="#ec4899" />
            </div>

            <h2 style={{ color: "rgba(255,255,255,0.7)", fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Подписки</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 32 }}>
                <StatCard label="VIP" value={stats.subscriptions.vip} color="#f59e0b" />
                <StatCard label="Premium" value={stats.subscriptions.premium} color="#8b5cf6" />
                <StatCard label="Без подписки" value={stats.subscriptions.free} />
            </div>

            <h2 style={{ color: "rgba(255,255,255,0.7)", fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Активность</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
                <StatCard label="Лайков сегодня" value={stats.activity.likes_today} />
                <StatCard label="Всего лайков" value={stats.activity.total_likes} />
                <StatCard label="Матчей" value={stats.activity.matches} color="#10b981" />
            </div>
        </div>
    );
}
