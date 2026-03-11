"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";

interface UserDetail {
    telegram_id: number;
    name?: string;
    username?: string;
    gender?: string;
    age?: number | string;
    city?: string;
    about?: string;
    is_active?: boolean;
    is_banned?: boolean;
    premium_type?: string;
    premium_until?: string;
    last_seen?: string;
    created_at?: string;
    photos?: string[];
    photo?: string;
    stats?: { likes_given: number; likes_received: number; matches: number };
    ban_reason?: string;
}

export default function AdminUserDetail() {
    const params = useParams();
    const router = useRouter();
    const userId = params.userId as string;

    const [user, setUser] = useState<UserDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [msg, setMsg] = useState("");
    const [premiumDays, setPremiumDays] = useState("30");
    const [premiumType, setPremiumType] = useState("vip");

    const adminKey = () => localStorage.getItem("kupidon_admin_key") || "";

    const fetchUser = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/admin/users/${userId}`, {
                headers: { "X-Admin-Key": adminKey() },
            });
            setUser(await res.json());
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchUser(); }, [userId]);

    const action = async (url: string, method: string, body?: object) => {
        await fetch(`${BackEnd_URL}${url}`, {
            method,
            headers: { "X-Admin-Key": adminKey(), "Content-Type": "application/json" },
            body: body ? JSON.stringify(body) : undefined,
        });
        await fetchUser();
    };

    const showMsg = (text: string) => { setMsg(text); setTimeout(() => setMsg(""), 3000); };

    if (loading) return <div style={{ padding: 32, color: "rgba(255,255,255,0.5)" }}>Загрузка...</div>;
    if (!user) return <div style={{ padding: 32, color: "#f87171" }}>Пользователь не найден</div>;

    const photoCount = user.photos?.length || (user.photo ? 1 : 0);

    return (
        <div style={{ padding: 32, maxWidth: 900 }}>
            <button onClick={() => router.back()} style={{
                background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
                color: "rgba(255,255,255,0.6)", borderRadius: 8, padding: "7px 14px", cursor: "pointer",
                fontSize: 13, marginBottom: 24,
            }}>← Назад</button>

            {msg && (
                <div style={{ background: "#065f46", borderRadius: 8, padding: "10px 16px", color: "#fff", marginBottom: 16, fontSize: 14 }}>
                    {msg}
                </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                {/* Карточка профиля */}
                <div style={{ background: "#1a1a2e", borderRadius: 16, padding: 24, border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
                        <div style={{
                            width: 72, height: 72, borderRadius: "50%",
                            background: "linear-gradient(135deg, #7c3aed, #ec4899)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 28, color: "#fff", fontWeight: 700,
                            overflow: "hidden",
                        }}>
                            {photoCount > 0
                                ? <img src={`${BackEnd_URL}/api/v1/users/${user.telegram_id}/photo/0`}
                                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                                    onError={e => { (e.target as HTMLImageElement).style.display = "none"; }} />
                                : (user.name?.[0]?.toUpperCase() || "?")}
                        </div>
                        <div>
                            <div style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>{user.name || "Без имени"}</div>
                            {user.username && <div style={{ color: "#a78bfa", fontSize: 13 }}>@{user.username}</div>}
                            <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, marginTop: 4, fontFamily: "monospace" }}>
                                ID: {user.telegram_id}
                            </div>
                        </div>
                    </div>

                    {[
                        ["Пол", user.gender || "—"],
                        ["Возраст", user.age || "—"],
                        ["Город", user.city || "—"],
                        ["Фотографий", photoCount],
                        ["Подписка", user.premium_type || "Нет"],
                        ["Подписка до", user.premium_until ? new Date(user.premium_until).toLocaleDateString("ru") : "—"],
                        ["Зарегистрирован", user.created_at ? new Date(user.created_at).toLocaleDateString("ru") : "—"],
                        ["Последняя активность", user.last_seen ? new Date(user.last_seen).toLocaleString("ru") : "—"],
                    ].map(([k, v]) => (
                        <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                            <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 13 }}>{k}</span>
                            <span style={{ color: "#fff", fontSize: 13 }}>{String(v)}</span>
                        </div>
                    ))}

                    {user.about && (
                        <div style={{ marginTop: 16 }}>
                            <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, marginBottom: 6 }}>О себе</div>
                            <div style={{ color: "rgba(255,255,255,0.8)", fontSize: 13, lineHeight: 1.5 }}>{user.about}</div>
                        </div>
                    )}
                </div>

                {/* Действия */}
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    {/* Статистика */}
                    {user.stats && (
                        <div style={{ background: "#1a1a2e", borderRadius: 16, padding: 20, border: "1px solid rgba(255,255,255,0.08)" }}>
                            <h3 style={{ color: "#fff", fontSize: 15, marginBottom: 16 }}>Активность</h3>
                            {[
                                ["Лайков отправил", user.stats.likes_given],
                                ["Лайков получил", user.stats.likes_received],
                                ["Матчей", user.stats.matches],
                            ].map(([k, v]) => (
                                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                                    <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 13 }}>{k}</span>
                                    <span style={{ color: "#fff", fontSize: 15, fontWeight: 700 }}>{v}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Управление подпиской */}
                    <div style={{ background: "#1a1a2e", borderRadius: 16, padding: 20, border: "1px solid rgba(255,255,255,0.08)" }}>
                        <h3 style={{ color: "#fff", fontSize: 15, marginBottom: 16 }}>Подписка</h3>
                        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                            <select value={premiumType} onChange={e => setPremiumType(e.target.value)} style={{ ...selectStyle, flex: 1 }}>
                                <option value="vip">VIP</option>
                                <option value="premium">Premium</option>
                            </select>
                            <input value={premiumDays} onChange={e => setPremiumDays(e.target.value)} type="number" min="1" max="365"
                                style={{ ...inputStyle, width: 80 }} placeholder="Дней" />
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                            <button onClick={async () => {
                                await action(`/api/v1/admin/users/${userId}/premium`, "PUT",
                                    { premium_type: premiumType, days: parseInt(premiumDays) || 30 });
                                showMsg(`${premiumType.toUpperCase()} выдан на ${premiumDays} дней`);
                            }} style={btnSuccess}>Выдать</button>
                            <button onClick={async () => {
                                await action(`/api/v1/admin/users/${userId}/premium`, "PUT", { premium_type: null, days: 0 });
                                showMsg("Подписка снята");
                            }} style={btnDanger}>Снять</button>
                        </div>
                    </div>

                    {/* Управление доступом */}
                    <div style={{ background: "#1a1a2e", borderRadius: 16, padding: 20, border: "1px solid rgba(255,255,255,0.08)" }}>
                        <h3 style={{ color: "#fff", fontSize: 15, marginBottom: 16 }}>Действия</h3>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            {user.is_banned ? (
                                <button onClick={async () => {
                                    await action(`/api/v1/admin/users/${userId}/ban`, "PUT", { ban: false });
                                    showMsg("Пользователь разблокирован");
                                }} style={btnSuccess}>✓ Разблокировать</button>
                            ) : (
                                <button onClick={async () => {
                                    await action(`/api/v1/admin/users/${userId}/ban`, "PUT", { ban: true });
                                    showMsg("Пользователь заблокирован");
                                }} style={btnDanger}>🚫 Заблокировать</button>
                            )}
                            <button onClick={async () => {
                                await action(`/api/v1/admin/users/${userId}/active`, "PUT", { active: !user.is_active });
                                showMsg(user.is_active ? "Анкета скрыта" : "Анкета активирована");
                            }} style={{ ...btnSmall, justifyContent: "center" }}>
                                {user.is_active ? "🙈 Скрыть анкету" : "👁 Показать анкету"}
                            </button>
                            <button onClick={async () => {
                                if (!confirm("Удалить пользователя? Действие необратимо!")) return;
                                await fetch(`${BackEnd_URL}/api/v1/admin/users/${userId}`, {
                                    method: "DELETE", headers: { "X-Admin-Key": adminKey() },
                                });
                                router.push("/admin/users");
                            }} style={{ ...btnDanger, background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.3)" }}>
                                🗑 Удалить навсегда
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

const inputStyle: React.CSSProperties = {
    padding: "9px 12px", borderRadius: 8,
    background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
    color: "#fff", fontSize: 13, outline: "none",
};
const selectStyle: React.CSSProperties = {
    padding: "9px 12px", borderRadius: 8,
    background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
    color: "#fff", fontSize: 13, outline: "none", cursor: "pointer",
};
const btnSuccess: React.CSSProperties = {
    flex: 1, padding: "9px", borderRadius: 8, border: "none",
    background: "rgba(16,185,129,0.2)", color: "#10b981", fontWeight: 600, fontSize: 13, cursor: "pointer",
};
const btnDanger: React.CSSProperties = {
    flex: 1, padding: "9px", borderRadius: 8, border: "none",
    background: "rgba(239,68,68,0.2)", color: "#f87171", fontWeight: 600, fontSize: 13, cursor: "pointer",
};
const btnSmall: React.CSSProperties = {
    padding: "9px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)",
    background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.7)", fontSize: 13, cursor: "pointer",
    display: "flex", alignItems: "center", gap: 6,
};
