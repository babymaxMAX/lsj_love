"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";

interface UserItem {
    telegram_id: number;
    name?: string;
    username?: string;
    gender?: string;
    age?: number | string;
    city?: string;
    is_active?: boolean;
    is_banned?: boolean;
    premium_type?: string;
    premium_until?: string;
    last_seen?: string;
    created_at?: string;
    photos?: string[];
}

export default function AdminUsers() {
    const router = useRouter();
    const [users, setUsers] = useState<UserItem[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [gender, setGender] = useState("");
    const [premium, setPremium] = useState("");
    const [banned, setBanned] = useState("");
    const [loading, setLoading] = useState(false);
    const [actionMsg, setActionMsg] = useState("");

    const adminKey = () => localStorage.getItem("kupidon_admin_key") || "";

    const fetchUsers = useCallback(async (pg = page) => {
        setLoading(true);
        const params = new URLSearchParams({
            page: String(pg), limit: "20",
            search, gender, premium, banned,
        });
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/admin/users?${params}`, {
                headers: { "X-Admin-Key": adminKey() },
            });
            const data = await res.json();
            setUsers(data.items || []);
            setTotal(data.total || 0);
        } catch {
            setUsers([]);
        } finally {
            setLoading(false);
        }
    }, [page, search, gender, premium, banned]);

    useEffect(() => { fetchUsers(); }, []);

    const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setPage(1); fetchUsers(1); };

    const banUser = async (uid: number, ban: boolean) => {
        await fetch(`${BackEnd_URL}/api/v1/admin/users/${uid}/ban`, {
            method: "PUT",
            headers: { "X-Admin-Key": adminKey(), "Content-Type": "application/json" },
            body: JSON.stringify({ ban }),
        });
        setActionMsg(ban ? `Пользователь ${uid} заблокирован` : `Пользователь ${uid} разблокирован`);
        fetchUsers();
        setTimeout(() => setActionMsg(""), 3000);
    };

    const deleteUser = async (uid: number) => {
        if (!confirm(`Удалить пользователя ${uid}? Действие необратимо.`)) return;
        await fetch(`${BackEnd_URL}/api/v1/admin/users/${uid}`, {
            method: "DELETE",
            headers: { "X-Admin-Key": adminKey() },
        });
        setActionMsg(`Пользователь ${uid} удалён`);
        fetchUsers();
        setTimeout(() => setActionMsg(""), 3000);
    };

    const grantVip = async (uid: number) => {
        await fetch(`${BackEnd_URL}/api/v1/admin/users/${uid}/premium`, {
            method: "PUT",
            headers: { "X-Admin-Key": adminKey(), "Content-Type": "application/json" },
            body: JSON.stringify({ premium_type: "vip", days: 30 }),
        });
        setActionMsg(`VIP выдан пользователю ${uid} на 30 дней`);
        fetchUsers();
        setTimeout(() => setActionMsg(""), 3000);
    };

    const totalPages = Math.ceil(total / 20);

    return (
        <div style={{ padding: "32px" }}>
            <h1 style={{ color: "#fff", fontSize: 24, fontWeight: 700, marginBottom: 24 }}>👥 Пользователи</h1>

            {actionMsg && (
                <div style={{ background: "#065f46", border: "1px solid #10b981", borderRadius: 8, padding: "10px 16px", color: "#fff", marginBottom: 16, fontSize: 14 }}>
                    {actionMsg}
                </div>
            )}

            {/* Поиск и фильтры */}
            <form onSubmit={handleSearch} style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 24 }}>
                <input
                    value={search} onChange={e => setSearch(e.target.value)}
                    placeholder="Имя, username или Telegram ID"
                    style={inputStyle}
                />
                <select value={gender} onChange={e => setGender(e.target.value)} style={selectStyle}>
                    <option value="">Все полы</option>
                    <option value="Man">Мужчины</option>
                    <option value="Female">Женщины</option>
                </select>
                <select value={premium} onChange={e => setPremium(e.target.value)} style={selectStyle}>
                    <option value="">Все тарифы</option>
                    <option value="vip">VIP</option>
                    <option value="premium">Premium</option>
                    <option value="free">Без подписки</option>
                </select>
                <select value={banned} onChange={e => setBanned(e.target.value)} style={selectStyle}>
                    <option value="">Все</option>
                    <option value="false">Активные</option>
                    <option value="true">Заблокированные</option>
                </select>
                <button type="submit" style={btnPrimary}>Найти</button>
            </form>

            <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 13, marginBottom: 16 }}>
                Найдено: {total}
            </div>

            {loading && <div style={{ color: "rgba(255,255,255,0.5)" }}>Загрузка...</div>}

            {/* Таблица */}
            <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                            {["ID", "Имя", "Пол", "Возраст", "Город", "Тариф", "Статус", "Действия"].map(h => (
                                <th key={h} style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, fontWeight: 600, textAlign: "left", padding: "8px 12px", textTransform: "uppercase" }}>
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {users.map(u => (
                            <tr key={u.telegram_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", transition: "background 0.1s" }}
                                onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.02)")}
                                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                                <td style={td}><span style={{ fontFamily: "monospace", fontSize: 12, color: "rgba(255,255,255,0.5)" }}>{u.telegram_id}</span></td>
                                <td style={td}>
                                    <button onClick={() => router.push(`/admin/users/${u.telegram_id}`)}
                                        style={{ background: "none", border: "none", color: "#a78bfa", cursor: "pointer", fontSize: 14, padding: 0 }}>
                                        {u.name || "—"}
                                    </button>
                                    {u.username && <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12 }}>@{u.username}</div>}
                                </td>
                                <td style={td}><span style={{ fontSize: 13, color: u.gender?.toLowerCase().includes("female") || u.gender?.includes("жен") ? "#ec4899" : "#3b82f6" }}>
                                    {u.gender?.toLowerCase().includes("female") || u.gender?.includes("жен") ? "♀" : "♂"}
                                </span></td>
                                <td style={td}><span style={{ color: "rgba(255,255,255,0.7)", fontSize: 13 }}>{u.age || "—"}</span></td>
                                <td style={td}><span style={{ color: "rgba(255,255,255,0.7)", fontSize: 13 }}>{u.city || "—"}</span></td>
                                <td style={td}>
                                    {u.premium_type === "vip" && <span style={badgeVip}>VIP</span>}
                                    {u.premium_type === "premium" && <span style={badgePremium}>Premium</span>}
                                    {!u.premium_type && <span style={badgeFree}>Free</span>}
                                </td>
                                <td style={td}>
                                    {u.is_banned ? <span style={badgeBanned}>Бан</span> :
                                        u.is_active ? <span style={badgeActive}>Активен</span> :
                                            <span style={badgeInactive}>Скрыт</span>}
                                </td>
                                <td style={td}>
                                    <div style={{ display: "flex", gap: 6 }}>
                                        <button onClick={() => router.push(`/admin/users/${u.telegram_id}`)} style={btnSmall}>Детали</button>
                                        {u.is_banned
                                            ? <button onClick={() => banUser(u.telegram_id, false)} style={{ ...btnSmall, background: "rgba(16,185,129,0.2)", color: "#10b981" }}>Разбан</button>
                                            : <button onClick={() => banUser(u.telegram_id, true)} style={{ ...btnSmall, background: "rgba(239,68,68,0.2)", color: "#ef4444" }}>Бан</button>
                                        }
                                        <button onClick={() => grantVip(u.telegram_id)} style={{ ...btnSmall, background: "rgba(245,158,11,0.2)", color: "#f59e0b" }}>VIP</button>
                                        <button onClick={() => deleteUser(u.telegram_id)} style={{ ...btnSmall, background: "rgba(239,68,68,0.1)", color: "#f87171" }}>✕</button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Пагинация */}
            {totalPages > 1 && (
                <div style={{ display: "flex", gap: 8, marginTop: 24, justifyContent: "center" }}>
                    <button disabled={page <= 1} onClick={() => { setPage(p => p - 1); fetchUsers(page - 1); }} style={btnPage}>←</button>
                    <span style={{ color: "rgba(255,255,255,0.5)", lineHeight: "32px", fontSize: 13 }}>
                        Стр. {page} / {totalPages}
                    </span>
                    <button disabled={page >= totalPages} onClick={() => { setPage(p => p + 1); fetchUsers(page + 1); }} style={btnPage}>→</button>
                </div>
            )}
        </div>
    );
}

const inputStyle: React.CSSProperties = {
    flex: 1, minWidth: 200, padding: "10px 14px", borderRadius: 8,
    background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
    color: "#fff", fontSize: 13, outline: "none",
};
const selectStyle: React.CSSProperties = {
    padding: "10px 14px", borderRadius: 8,
    background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
    color: "#fff", fontSize: 13, outline: "none", cursor: "pointer",
};
const btnPrimary: React.CSSProperties = {
    padding: "10px 20px", borderRadius: 8, border: "none",
    background: "linear-gradient(135deg, #7c3aed, #ec4899)",
    color: "#fff", fontWeight: 600, fontSize: 13, cursor: "pointer",
};
const td: React.CSSProperties = { padding: "12px 12px", color: "#fff", fontSize: 14, verticalAlign: "middle" };
const btnSmall: React.CSSProperties = {
    padding: "5px 10px", borderRadius: 6, border: "none",
    background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)",
    fontSize: 12, cursor: "pointer",
};
const btnPage: React.CSSProperties = {
    width: 32, height: 32, borderRadius: 6, border: "1px solid rgba(255,255,255,0.15)",
    background: "rgba(255,255,255,0.05)", color: "#fff", cursor: "pointer", fontSize: 15,
};
const badgeVip: React.CSSProperties = { background: "rgba(245,158,11,0.2)", color: "#f59e0b", padding: "2px 8px", borderRadius: 99, fontSize: 11, fontWeight: 700 };
const badgePremium: React.CSSProperties = { background: "rgba(139,92,246,0.2)", color: "#a78bfa", padding: "2px 8px", borderRadius: 99, fontSize: 11, fontWeight: 700 };
const badgeFree: React.CSSProperties = { background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.4)", padding: "2px 8px", borderRadius: 99, fontSize: 11 };
const badgeActive: React.CSSProperties = { background: "rgba(16,185,129,0.15)", color: "#10b981", padding: "2px 8px", borderRadius: 99, fontSize: 11 };
const badgeInactive: React.CSSProperties = { background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.4)", padding: "2px 8px", borderRadius: 99, fontSize: 11 };
const badgeBanned: React.CSSProperties = { background: "rgba(239,68,68,0.2)", color: "#f87171", padding: "2px 8px", borderRadius: 99, fontSize: 11, fontWeight: 700 };
