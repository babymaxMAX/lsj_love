"use client";
import { useState } from "react";
import { BackEnd_URL } from "@/config/url";

export default function AdminBroadcast() {
    const [text, setText] = useState("");
    const [photoUrl, setPhotoUrl] = useState("");
    const [target, setTarget] = useState("all");
    const [sending, setSending] = useState(false);
    const [result, setResult] = useState<{ sent: number; failed: number; total: number } | null>(null);
    const [error, setError] = useState("");

    const adminKey = () => localStorage.getItem("kupidon_admin_key") || "";

    const send = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!text.trim()) { setError("Введите текст сообщения"); return; }
        if (!confirm(`Отправить рассылку ${target === "all" ? "всем пользователям" : `группе "${target}"`}?`)) return;

        setSending(true);
        setResult(null);
        setError("");
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/admin/broadcast`, {
                method: "POST",
                headers: { "X-Admin-Key": adminKey(), "Content-Type": "application/json" },
                body: JSON.stringify({ text, photo_url: photoUrl || undefined, target, parse_mode: "HTML" }),
            });
            const data = await res.json();
            if (!res.ok) { setError(data.detail || "Ошибка"); return; }
            setResult(data);
        } catch {
            setError("Ошибка соединения");
        } finally {
            setSending(false);
        }
    };

    const targetLabels: Record<string, string> = {
        all: "Всем пользователям",
        premium: "Только Premium",
        vip: "Только VIP",
        active_7d: "Активным за 7 дней",
        no_premium: "Без подписки",
    };

    return (
        <div style={{ padding: 32, maxWidth: 700 }}>
            <h1 style={{ color: "#fff", fontSize: 24, fontWeight: 700, marginBottom: 8 }}>📢 Рассылка</h1>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginBottom: 32 }}>
                Отправляет сообщение через Telegram бот. Поддерживается HTML-форматирование.
            </p>

            {result && (
                <div style={{ background: "#065f46", borderRadius: 12, padding: 20, marginBottom: 24, border: "1px solid #10b981" }}>
                    <div style={{ color: "#10b981", fontWeight: 700, fontSize: 16, marginBottom: 8 }}>✓ Рассылка завершена</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                        {[["Отправлено", result.sent, "#10b981"], ["Ошибок", result.failed, "#f87171"], ["Всего", result.total, "#fff"]].map(([l, v, c]) => (
                            <div key={l as string}>
                                <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 12 }}>{l}</div>
                                <div style={{ color: c as string, fontSize: 24, fontWeight: 700 }}>{v}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {error && (
                <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, padding: "10px 16px", color: "#f87171", marginBottom: 16 }}>
                    {error}
                </div>
            )}

            <form onSubmit={send} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                <div>
                    <label style={{ color: "rgba(255,255,255,0.7)", fontSize: 13, display: "block", marginBottom: 8, fontWeight: 600 }}>
                        Аудитория
                    </label>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                        {Object.entries(targetLabels).map(([val, label]) => (
                            <button key={val} type="button" onClick={() => setTarget(val)} style={{
                                padding: "10px 16px", borderRadius: 8, cursor: "pointer", fontSize: 13,
                                border: target === val ? "1px solid #7c3aed" : "1px solid rgba(255,255,255,0.1)",
                                background: target === val ? "rgba(124,58,237,0.3)" : "rgba(255,255,255,0.05)",
                                color: target === val ? "#a78bfa" : "rgba(255,255,255,0.6)",
                                fontWeight: target === val ? 600 : 400,
                            }}>
                                {label}
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <label style={{ color: "rgba(255,255,255,0.7)", fontSize: 13, display: "block", marginBottom: 8, fontWeight: 600 }}>
                        Текст сообщения (HTML)
                    </label>
                    <textarea
                        value={text} onChange={e => setText(e.target.value)}
                        placeholder={'<b>Привет!</b>\nНовости Kupidon AI:\n\n• Новая функция AI подбора\n• Скидка 50% на VIP'}
                        rows={8}
                        style={{
                            width: "100%", padding: "12px 16px", borderRadius: 10, outline: "none",
                            background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
                            color: "#fff", fontSize: 14, resize: "vertical", boxSizing: "border-box",
                            fontFamily: "monospace", lineHeight: 1.6,
                        }}
                        required
                    />
                    <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 12, marginTop: 4 }}>
                        Поддерживается: &lt;b&gt;, &lt;i&gt;, &lt;a href=""&gt;, &lt;code&gt;
                    </div>
                </div>

                <div>
                    <label style={{ color: "rgba(255,255,255,0.7)", fontSize: 13, display: "block", marginBottom: 8, fontWeight: 600 }}>
                        URL фото (необязательно)
                    </label>
                    <input
                        type="url" value={photoUrl} onChange={e => setPhotoUrl(e.target.value)}
                        placeholder="https://example.com/image.jpg"
                        style={{
                            width: "100%", padding: "10px 16px", borderRadius: 8, outline: "none", boxSizing: "border-box",
                            background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
                            color: "#fff", fontSize: 13,
                        }}
                    />
                </div>

                <div style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: 8, padding: "12px 16px" }}>
                    <span style={{ color: "#f59e0b", fontSize: 13 }}>
                        ⚠️ Рассылка отправляет сообщения <b>всем выбранным пользователям</b> напрямую в Telegram.
                        Убедитесь что текст правильный перед отправкой.
                    </span>
                </div>

                <button type="submit" disabled={sending} style={{
                    padding: "14px", borderRadius: 10, border: "none",
                    background: sending ? "rgba(255,255,255,0.1)" : "linear-gradient(135deg, #7c3aed, #ec4899)",
                    color: "#fff", fontWeight: 700, fontSize: 15, cursor: sending ? "not-allowed" : "pointer",
                }}>
                    {sending ? "Отправка..." : `🚀 Отправить — ${targetLabels[target]}`}
                </button>
            </form>
        </div>
    );
}
