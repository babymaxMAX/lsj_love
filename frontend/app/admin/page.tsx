"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";

const ADMIN_KEY_STORAGE = "kupidon_admin_key";

export default function AdminLogin() {
    const [key, setKey] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    // Если ключ уже сохранён — проверяем и перенаправляем
    useEffect(() => {
        const saved = localStorage.getItem(ADMIN_KEY_STORAGE);
        if (saved) {
            fetch(`${BackEnd_URL}/api/v1/admin/stats`, {
                headers: { "X-Admin-Key": saved },
            }).then(r => {
                if (r.ok) router.push("/admin/dashboard");
            });
        }
    }, [router]);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/admin/stats`, {
                headers: { "X-Admin-Key": key },
            });
            if (res.ok) {
                localStorage.setItem(ADMIN_KEY_STORAGE, key);
                router.push("/admin/dashboard");
            } else {
                setError("Неверный ключ доступа");
            }
        } catch {
            setError("Ошибка соединения");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ minHeight: "100vh", background: "#0f0f1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ background: "#1a1a2e", borderRadius: 16, padding: 40, width: 360, border: "1px solid rgba(255,255,255,0.1)" }}>
                <h1 style={{ color: "#fff", fontSize: 24, fontWeight: 700, marginBottom: 8, textAlign: "center" }}>
                    Kupidon AI
                </h1>
                <p style={{ color: "rgba(255,255,255,0.5)", textAlign: "center", marginBottom: 32, fontSize: 14 }}>
                    Панель администратора
                </p>
                <form onSubmit={handleLogin}>
                    <input
                        type="password"
                        placeholder="Секретный ключ"
                        value={key}
                        onChange={e => setKey(e.target.value)}
                        style={{
                            width: "100%", padding: "12px 16px", borderRadius: 10,
                            background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)",
                            color: "#fff", fontSize: 15, marginBottom: 16, boxSizing: "border-box",
                            outline: "none",
                        }}
                        required
                    />
                    {error && <p style={{ color: "#f87171", fontSize: 14, marginBottom: 12 }}>{error}</p>}
                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: "100%", padding: "13px", borderRadius: 10, border: "none",
                            background: "linear-gradient(135deg, #7c3aed, #ec4899)",
                            color: "#fff", fontWeight: 700, fontSize: 15, cursor: "pointer",
                        }}
                    >
                        {loading ? "Вход..." : "Войти"}
                    </button>
                </form>
            </div>
        </div>
    );
}
