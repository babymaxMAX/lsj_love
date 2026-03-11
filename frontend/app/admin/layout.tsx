"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { BackEnd_URL } from "@/config/url";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [ready, setReady] = useState(false);

    useEffect(() => {
        if (pathname === "/admin") { setReady(true); return; }
        const key = localStorage.getItem("kupidon_admin_key");
        if (!key) { router.push("/admin"); return; }
        fetch(`${BackEnd_URL}/api/v1/admin/stats`, {
            headers: { "X-Admin-Key": key },
        }).then(r => {
            if (!r.ok) router.push("/admin");
            else setReady(true);
        }).catch(() => router.push("/admin"));
    }, [pathname, router]);

    const logout = () => {
        localStorage.removeItem("kupidon_admin_key");
        router.push("/admin");
    };

    if (!ready) return (
        <div style={{ minHeight: "100vh", background: "#0f0f1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ color: "rgba(255,255,255,0.5)" }}>Загрузка...</div>
        </div>
    );

    if (pathname === "/admin") return <>{children}</>;

    const navItems = [
        { href: "/admin/dashboard", label: "📊 Статистика" },
        { href: "/admin/users", label: "👥 Пользователи" },
        { href: "/admin/broadcast", label: "📢 Рассылка" },
    ];

    return (
        <div style={{ minHeight: "100vh", background: "#0f0f1a", display: "flex" }}>
            {/* Sidebar */}
            <div style={{
                width: 220, background: "#1a1a2e", borderRight: "1px solid rgba(255,255,255,0.08)",
                padding: "24px 0", display: "flex", flexDirection: "column", flexShrink: 0,
            }}>
                <div style={{ padding: "0 20px 24px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                    <div style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>Kupidon AI</div>
                    <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, marginTop: 4 }}>Admin Panel</div>
                </div>
                <nav style={{ flex: 1, padding: "16px 12px" }}>
                    {navItems.map(item => (
                        <Link key={item.href} href={item.href} style={{
                            display: "block", padding: "10px 12px", borderRadius: 8, marginBottom: 4,
                            color: pathname === item.href ? "#fff" : "rgba(255,255,255,0.6)",
                            background: pathname === item.href ? "rgba(124,58,237,0.3)" : "transparent",
                            textDecoration: "none", fontSize: 14, fontWeight: pathname === item.href ? 600 : 400,
                            transition: "all 0.15s",
                        }}>
                            {item.label}
                        </Link>
                    ))}
                </nav>
                <div style={{ padding: "16px 12px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                    <button onClick={logout} style={{
                        width: "100%", padding: "10px", borderRadius: 8, border: "none",
                        background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.5)",
                        cursor: "pointer", fontSize: 14,
                    }}>
                        Выйти
                    </button>
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: "auto" }}>
                {children}
            </div>
        </div>
    );
}
