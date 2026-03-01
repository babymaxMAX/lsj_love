"use client";
import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";
import { BottomNav } from "@/components/bottom-nav";

interface Answer { question_id: string; text: string; emoji: string; answer: string | string[]; }
interface ChatMsg { role: "user" | "assistant"; content: string; }

export default function SettingsPage() {
    const params = useParams();
    const router = useRouter();
    const userId = params.users as string;

    const [user, setUser] = useState<any>(null);
    const [answers, setAnswers] = useState<Answer[]>([]);
    const [tab, setTab] = useState<"info" | "answers" | "ai">("info");
    const [about, setAbout] = useState("");
    const [name, setName] = useState("");
    const [city, setCity] = useState("");
    const [saving, setSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState("");

    // AI builder
    const [aiAccess, setAiAccess] = useState<any>(null);
    const [aiMessages, setAiMessages] = useState<ChatMsg[]>([
        { role: "assistant", content: "Привет! 🤖 Я помогу тебе создать привлекательную анкету.\n\nРасскажи о себе — чем занимаешься, что любишь, кого ищешь. Я сформулирую красивое описание для профиля!" },
    ]);
    const [aiInput, setAiInput] = useState("");
    const [aiLoading, setAiLoading] = useState(false);
    const aiBottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/users/${userId}`).then(r => r.json()).then(d => {
            setUser(d);
            setAbout(d.about || "");
            setName(d.name || "");
            setCity(d.city || "");
        }).catch(() => {});
        fetch(`${BackEnd_URL}/api/v1/profile/answers/${userId}`).then(r => r.json()).then(d => setAnswers(d.answers || [])).catch(() => {});
        fetch(`${BackEnd_URL}/api/v1/profile/ai-builder/status/${userId}`).then(r => r.json()).then(setAiAccess).catch(() => {});
    }, [userId]);

    useEffect(() => { aiBottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [aiMessages]);

    const saveProfile = async () => {
        setSaving(true); setSaveMsg("");
        try {
            await fetch(`${BackEnd_URL}/api/v1/users/${userId}/profile`, {
                method: "PATCH", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ about, name, city }),
            });
            setSaveMsg("✅ Сохранено!");
            setTimeout(() => setSaveMsg(""), 2000);
        } catch { setSaveMsg("Ошибка"); }
        setSaving(false);
    };

    const deleteAnswer = async (qid: string) => {
        await fetch(`${BackEnd_URL}/api/v1/profile/answers`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ telegram_id: parseInt(userId), question_id: qid, answer: "" }),
        });
        setAnswers(prev => prev.filter(a => a.question_id !== qid));
    };

    const sendAiMessage = async () => {
        const text = aiInput.trim();
        if (!text || aiLoading) return;
        setAiInput("");
        const userMsg: ChatMsg = { role: "user", content: text };
        setAiMessages(prev => [...prev, userMsg, { role: "assistant", content: "..." }]);
        setAiLoading(true);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/profile/ai-builder/chat`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ telegram_id: parseInt(userId), message: text, history: aiMessages }),
            });
            const d = await res.json();
            if (d.blocked) { setAiAccess({ access: false, trial_expired: true }); }
            if (d.saved_about) { setAbout(d.saved_about); }
            setAiMessages(prev => [...prev.slice(0, -1), { role: "assistant", content: d.reply }]);
        } catch { setAiMessages(prev => [...prev.slice(0, -1), { role: "assistant", content: "Ошибка. Попробуй снова." }]); }
        setAiLoading(false);
    };

    const tabStyle = (t: string) => ({
        flex: 1, padding: "10px 0", borderRadius: 12, fontWeight: 700, fontSize: 13, border: "none", cursor: "pointer",
        background: tab === t ? "linear-gradient(135deg, #7c3aed, #db2777)" : "rgba(255,255,255,0.06)",
        color: tab === t ? "#fff" : "rgba(255,255,255,0.5)",
    });

    if (!user) return <div className="flex items-center justify-center h-screen" style={{ background: "#0f0f1a" }}><div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" /></div>;

    return (
        <div className="flex flex-col min-h-screen pb-24" style={{ background: "#0f0f1a", color: "#fff" }}>
            <div className="sticky top-0 z-30 flex items-center gap-3 px-4" style={{ background: "rgba(15,15,26,0.97)", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingTop: 4, paddingBottom: 12 }}>
                <button onClick={() => router.back()} style={{ width: 36, height: 36, borderRadius: 12, background: "rgba(255,255,255,0.08)", border: "none", color: "#fff", fontSize: 18, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>←</button>
                <h1 style={{ fontSize: 17, fontWeight: 700 }}>⚙️ Настройки профиля</h1>
            </div>

            {/* Tabs */}
            <div style={{ display: "flex", gap: 6, padding: "12px 16px 0" }}>
                <button onClick={() => setTab("info")} style={tabStyle("info")}>📝 Профиль</button>
                <button onClick={() => setTab("answers")} style={tabStyle("answers")}>💬 Обо мне</button>
                <button onClick={() => setTab("ai")} style={tabStyle("ai")}>🤖 AI</button>
            </div>

            <div style={{ padding: "16px", flex: 1 }}>
                {tab === "info" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        <div>
                            <label style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginBottom: 4, display: "block" }}>Имя</label>
                            <input value={name} onChange={e => setName(e.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: 14, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.06)", color: "#fff", fontSize: 15, outline: "none" }} />
                        </div>
                        <div>
                            <label style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginBottom: 4, display: "block" }}>Город</label>
                            <input value={city} onChange={e => setCity(e.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: 14, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.06)", color: "#fff", fontSize: 15, outline: "none" }} />
                        </div>
                        <div>
                            <label style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginBottom: 4, display: "block" }}>О себе</label>
                            <textarea value={about} onChange={e => setAbout(e.target.value)} rows={4} style={{ width: "100%", padding: "12px 14px", borderRadius: 14, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.06)", color: "#fff", fontSize: 15, outline: "none", resize: "none" }} />
                        </div>
                        <button onClick={() => router.push(`/users/${userId}/profile`)} style={{ padding: "12px", borderRadius: 14, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", fontWeight: 600, fontSize: 14, cursor: "pointer" }}>📷 Изменить фото</button>
                        <button onClick={saveProfile} disabled={saving} style={{ padding: "14px", borderRadius: 16, background: "linear-gradient(135deg, #7c3aed, #db2777)", color: "#fff", fontWeight: 800, fontSize: 15, border: "none", cursor: "pointer", opacity: saving ? 0.6 : 1 }}>{saving ? "⏳" : "Сохранить изменения"}</button>
                        {saveMsg && <p style={{ textAlign: "center", fontSize: 14, color: "#86efac" }}>{saveMsg}</p>}
                    </div>
                )}

                {tab === "answers" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        <p style={{ fontSize: 13, color: "rgba(255,255,255,0.5)" }}>Ответы на вопросы — отображаются в профиле как теги "Обо мне"</p>
                        {answers.length === 0 && <p style={{ color: "rgba(255,255,255,0.4)", textAlign: "center", padding: "20px 0" }}>Нет ответов. Нажми ❓ на главном экране чтобы ответить на вопросы.</p>}
                        {answers.map(a => (
                            <div key={a.question_id} style={{ background: "rgba(255,255,255,0.06)", borderRadius: 16, padding: "12px 14px", display: "flex", alignItems: "center", gap: 10 }}>
                                <span style={{ fontSize: 20 }}>{a.emoji}</span>
                                <div style={{ flex: 1 }}>
                                    <p style={{ fontSize: 12, color: "rgba(255,255,255,0.4)" }}>{a.text}</p>
                                    <p style={{ fontSize: 14, fontWeight: 600 }}>{Array.isArray(a.answer) ? a.answer.join(", ") : a.answer}</p>
                                </div>
                                <button onClick={() => deleteAnswer(a.question_id)} style={{ width: 28, height: 28, borderRadius: 8, background: "rgba(239,68,68,0.2)", border: "none", color: "#ef4444", fontSize: 14, cursor: "pointer" }}>✕</button>
                            </div>
                        ))}
                    </div>
                )}

                {tab === "ai" && (
                    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 200px)" }}>
                        {aiAccess && !aiAccess.access ? (
                            <div style={{ textAlign: "center", padding: "40px 20px" }}>
                                <div style={{ fontSize: 48, marginBottom: 12 }}>🔒</div>
                                <p style={{ fontWeight: 700, fontSize: 16, marginBottom: 8 }}>AI-настройка профиля</p>
                                <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, marginBottom: 16 }}>Пробный период истёк. Оформи Premium для доступа.</p>
                                <button onClick={() => router.push(`/users/${userId}/premium`)} style={{ padding: "12px 24px", borderRadius: 16, background: "linear-gradient(135deg, #7c3aed, #db2777)", color: "#fff", fontWeight: 700, border: "none", cursor: "pointer" }}>⭐ Получить Premium</button>
                            </div>
                        ) : (
                            <>
                                {aiAccess?.trial_active && !aiAccess?.is_premium && (
                                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", textAlign: "center", padding: "4px 0" }}>⏳ Пробный период: {aiAccess.hours_left}ч</div>
                                )}
                                <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, paddingBottom: 8 }}>
                                    {aiMessages.map((m, i) => (
                                        <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                                            <div style={{
                                                maxWidth: "85%", padding: "10px 14px", borderRadius: 16, fontSize: 14, lineHeight: 1.5,
                                                background: m.role === "user" ? "linear-gradient(135deg, #7c3aed, #ec4899)" : "rgba(255,255,255,0.07)",
                                                color: "#fff", whiteSpace: "pre-wrap",
                                            }}>{m.content}</div>
                                        </div>
                                    ))}
                                    <div ref={aiBottomRef} />
                                </div>
                                <div style={{ display: "flex", gap: 8 }}>
                                    <input value={aiInput} onChange={e => setAiInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendAiMessage()} placeholder="Расскажи о себе..." disabled={aiLoading} style={{ flex: 1, padding: "11px 14px", borderRadius: 14, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#fff", fontSize: 14, outline: "none" }} />
                                    <button onClick={sendAiMessage} disabled={!aiInput.trim() || aiLoading} style={{ width: 44, height: 44, borderRadius: 14, background: "linear-gradient(135deg, #7c3aed, #ec4899)", border: "none", color: "#fff", fontSize: 18, cursor: "pointer", opacity: aiInput.trim() ? 1 : 0.4 }}>→</button>
                                </div>
                            </>
                        )}
                    </div>
                )}
            </div>

            <BottomNav userId={userId} />
        </div>
    );
}
