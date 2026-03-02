"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BackEnd_URL } from "@/config/url";

const PRESET_QUESTIONS = [
    { question: "Как проводишь выходные?", emoji: "🌅" },
    { question: "Ты сова или жаворонок?", emoji: "🌙" },
    { question: "Любимый жанр кино?", emoji: "🎬" },
    { question: "Твоя суперсила?", emoji: "⚡" },
    { question: "Что тебя вдохновляет?", emoji: "✨" },
    { question: "Любимое место отдыха?", emoji: "🏖️" },
];

interface QuizAnswer {
    question: string;
    answer: string;
    emoji: string;
}

interface UserData {
    name: string;
    city: string;
    about: string;
}

export default function ProfileSettingsPage({ params }: { params: { users: string } }) {
    const userId = params.users;
    const router = useRouter();
    const [tab, setTab] = useState<"profile" | "questions" | "ai">("profile");

    // Profile tab state
    const [userData, setUserData] = useState<UserData>({ name: "", city: "", about: "" });
    const [profileSaving, setProfileSaving] = useState(false);
    const [profileSaved, setProfileSaved] = useState(false);
    const [profileError, setProfileError] = useState<string | null>(null);

    // Questions tab state
    const [answers, setAnswers] = useState<QuizAnswer[]>([]);
    const [editingIdx, setEditingIdx] = useState<number | null>(null);
    const [editText, setEditText] = useState("");
    const [addingQuestion, setAddingQuestion] = useState(false);
    const [selectedPreset, setSelectedPreset] = useState<string>("");
    const [newAnswer, setNewAnswer] = useState("");
    const [questionsSaving, setQuestionsSaving] = useState(false);
    const [questionsSaved, setQuestionsSaved] = useState(false);

    // Load user data
    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/users/${userId}`)
            .then(r => r.json())
            .then(d => setUserData({ name: d.name || "", city: d.city || "", about: d.about || "" }))
            .catch(() => {});
    }, [userId]);

    // Load quiz answers
    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/users/${userId}/quiz-answers`)
            .then(r => r.ok ? r.json() : null)
            .then(d => d && setAnswers(d.answers || []))
            .catch(() => {});
    }, [userId]);

    const saveProfile = async () => {
        setProfileSaving(true);
        setProfileError(null);
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/users/${userId}/profile`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: userData.name,
                    city: userData.city,
                    about: userData.about,
                }),
            });
            if (!res.ok) {
                const d = await res.json();
                setProfileError(d?.detail || "Ошибка сохранения");
                return;
            }
            setProfileSaved(true);
            setTimeout(() => setProfileSaved(false), 2500);
        } catch {
            setProfileError("Ошибка соединения");
        } finally {
            setProfileSaving(false);
        }
    };

    const saveAnswers = async (updatedAnswers: QuizAnswer[]) => {
        setQuestionsSaving(true);
        try {
            await fetch(`${BackEnd_URL}/api/v1/users/${userId}/quiz-answers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ answers: updatedAnswers }),
            });
            setAnswers(updatedAnswers);
            setQuestionsSaved(true);
            setTimeout(() => setQuestionsSaved(false), 2000);
        } catch {
        } finally {
            setQuestionsSaving(false);
        }
    };

    const deleteAnswer = async (idx: number) => {
        const updated = answers.filter((_, i) => i !== idx);
        await saveAnswers(updated);
    };

    const saveEditedAnswer = async () => {
        if (editingIdx === null || !editText.trim()) return;
        const updated = answers.map((a, i) =>
            i === editingIdx ? { ...a, answer: editText.trim() } : a
        );
        await saveAnswers(updated);
        setEditingIdx(null);
        setEditText("");
    };

    const addNewAnswer = async () => {
        if (!selectedPreset || !newAnswer.trim()) return;
        const preset = PRESET_QUESTIONS.find(q => q.question === selectedPreset);
        if (!preset) return;
        const alreadyExists = answers.some(a => a.question === selectedPreset);
        let updated: QuizAnswer[];
        if (alreadyExists) {
            updated = answers.map(a =>
                a.question === selectedPreset ? { ...a, answer: newAnswer.trim() } : a
            );
        } else {
            updated = [...answers, { question: preset.question, answer: newAnswer.trim(), emoji: preset.emoji }];
        }
        await saveAnswers(updated);
        setAddingQuestion(false);
        setSelectedPreset("");
        setNewAnswer("");
    };

    return (
        <div className="flex flex-col min-h-screen pb-6" style={{ background: "#0f0f1a", color: "#fff" }}>
            {/* Header */}
            <div
                className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3"
                style={{ background: "rgba(15,15,26,0.97)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(255,255,255,0.07)" }}
            >
                <button
                    onClick={() => router.back()}
                    className="w-9 h-9 rounded-xl flex items-center justify-center transition-all active:scale-90"
                    style={{ background: "rgba(255,255,255,0.08)" }}
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                        <path d="M15 18l-6-6 6-6" />
                    </svg>
                </button>
                <div className="flex items-center gap-2">
                    <span className="text-lg">⚙️</span>
                    <h1 className="text-base font-bold">Настройки профиля</h1>
                </div>
            </div>

            {/* Tabs — FULLY VISIBLE, labeled, with padding */}
            <div className="px-4 pt-4 pb-2">
                <div className="flex rounded-2xl overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                    {[
                        { id: "profile", label: "👤 Профиль" },
                        { id: "questions", label: "💬 Вопросы" },
                        { id: "ai", label: "🤖 AI Анкета" },
                    ].map(t => (
                        <button
                            key={t.id}
                            onClick={() => setTab(t.id as "profile" | "questions" | "ai")}
                            className="flex-1 py-2.5 text-xs font-semibold transition-all"
                            style={{
                                background: tab === t.id ? "linear-gradient(135deg, #7c3aed, #a855f7)" : "transparent",
                                color: tab === t.id ? "#fff" : "rgba(255,255,255,0.45)",
                                borderRadius: 12,
                            }}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── TAB: Профиль ── */}
            {tab === "profile" && (
                <div className="px-4 pt-3 space-y-4">
                    <p className="text-xs text-white/40">Изменения сохраняются в вашем профиле</p>

                    {profileError && (
                        <div className="px-3 py-2.5 rounded-xl text-sm text-red-300" style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }}>
                            {profileError}
                        </div>
                    )}

                    <div className="space-y-3">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Имя</label>
                            <input
                                value={userData.name}
                                onChange={e => setUserData(p => ({ ...p, name: e.target.value }))}
                                placeholder="Ваше имя"
                                className="w-full rounded-xl px-4 py-3 text-sm text-white outline-none transition-all"
                                style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)" }}
                            />
                        </div>

                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Город</label>
                            <input
                                value={userData.city}
                                onChange={e => setUserData(p => ({ ...p, city: e.target.value }))}
                                placeholder="Ваш город"
                                className="w-full rounded-xl px-4 py-3 text-sm text-white outline-none transition-all"
                                style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)" }}
                            />
                        </div>

                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">О себе</label>
                            <textarea
                                value={userData.about}
                                onChange={e => setUserData(p => ({ ...p, about: e.target.value }))}
                                placeholder="Расскажи о себе..."
                                rows={4}
                                className="w-full rounded-xl px-4 py-3 text-sm text-white outline-none transition-all resize-none"
                                style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)" }}
                            />
                        </div>
                    </div>

                    <button
                        onClick={saveProfile}
                        disabled={profileSaving}
                        className="w-full py-3.5 rounded-2xl text-sm font-bold text-white transition-all active:scale-95"
                        style={{
                            background: profileSaved
                                ? "rgba(34,197,94,0.4)"
                                : "linear-gradient(135deg, #7c3aed, #a855f7)",
                            opacity: profileSaving ? 0.7 : 1,
                        }}
                    >
                        {profileSaving ? "Сохраняем..." : profileSaved ? "✅ Сохранено!" : "Сохранить изменения"}
                    </button>
                </div>
            )}

            {/* ── TAB: Вопросы ── */}
            {tab === "questions" && (
                <div className="px-4 pt-3 space-y-3">
                    <p className="text-xs text-white/40 leading-relaxed">
                        Ответы на вопросы отображаются в вашем профиле как теги «Обо мне» — это помогает другим лучше вас понять
                    </p>

                    {answers.length === 0 && !addingQuestion && (
                        <div className="py-8 flex flex-col items-center gap-3 text-center">
                            <span className="text-4xl">💬</span>
                            <p className="text-sm text-white/50">Нет ответов на вопросы</p>
                            <p className="text-xs text-white/30">Добавь ответы чтобы сделать профиль живее</p>
                        </div>
                    )}

                    {/* Answers list */}
                    {answers.map((a, i) => (
                        <div key={i} className="rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}>
                            <div className="flex items-start justify-between gap-2 mb-2">
                                <div className="flex items-center gap-2">
                                    <span>{a.emoji}</span>
                                    <p className="text-xs text-white/50">{a.question}</p>
                                </div>
                                <button
                                    onClick={() => deleteAnswer(i)}
                                    className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 transition-all active:scale-90"
                                    style={{ background: "rgba(239,68,68,0.25)" }}
                                >
                                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2.5">
                                        <path d="M18 6L6 18M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>

                            {editingIdx === i ? (
                                <div className="space-y-2">
                                    <textarea
                                        value={editText}
                                        onChange={e => setEditText(e.target.value)}
                                        rows={2}
                                        autoFocus
                                        className="w-full rounded-xl px-3 py-2 text-sm text-white outline-none resize-none"
                                        style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(124,58,237,0.5)" }}
                                    />
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => { setEditingIdx(null); setEditText(""); }}
                                            className="flex-1 py-2 rounded-xl text-xs font-semibold text-white/50 transition-all"
                                            style={{ background: "rgba(255,255,255,0.08)" }}
                                        >
                                            Отмена
                                        </button>
                                        <button
                                            onClick={saveEditedAnswer}
                                            disabled={questionsSaving || !editText.trim()}
                                            className="flex-1 py-2 rounded-xl text-xs font-semibold text-white transition-all"
                                            style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)", opacity: !editText.trim() ? 0.5 : 1 }}
                                        >
                                            {questionsSaving ? "..." : "Сохранить"}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-center justify-between gap-2">
                                    <p className="text-sm font-medium text-white/90 flex-1">{a.answer}</p>
                                    <button
                                        onClick={() => { setEditingIdx(i); setEditText(a.answer); }}
                                        className="text-xs px-2.5 py-1 rounded-lg transition-all active:scale-90"
                                        style={{ background: "rgba(124,58,237,0.25)", color: "#c084fc" }}
                                    >
                                        Изменить
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}

                    {questionsSaved && (
                        <p className="text-center text-sm text-green-400">✅ Сохранено!</p>
                    )}

                    {/* Add new answer */}
                    {addingQuestion ? (
                        <div className="rounded-2xl p-4 space-y-3" style={{ background: "rgba(124,58,237,0.1)", border: "1px solid rgba(124,58,237,0.3)" }}>
                            <p className="text-sm font-semibold text-white/80">Выбери вопрос:</p>
                            <div className="space-y-2">
                                {PRESET_QUESTIONS.filter(q => !answers.some(a => a.question === q.question)).map(q => (
                                    <button
                                        key={q.question}
                                        onClick={() => setSelectedPreset(q.question)}
                                        className="w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all"
                                        style={{
                                            background: selectedPreset === q.question ? "rgba(124,58,237,0.4)" : "rgba(255,255,255,0.06)",
                                            border: `1px solid ${selectedPreset === q.question ? "rgba(124,58,237,0.6)" : "transparent"}`,
                                        }}
                                    >
                                        {q.emoji} {q.question}
                                    </button>
                                ))}
                            </div>

                            {selectedPreset && (
                                <div>
                                    <label className="text-xs text-white/50 mb-1.5 block">Твой ответ:</label>
                                    <textarea
                                        value={newAnswer}
                                        onChange={e => setNewAnswer(e.target.value)}
                                        placeholder="Напиши свой ответ..."
                                        rows={2}
                                        className="w-full rounded-xl px-3 py-2 text-sm text-white outline-none resize-none"
                                        style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(124,58,237,0.4)" }}
                                    />
                                </div>
                            )}

                            <div className="flex gap-2">
                                <button
                                    onClick={() => { setAddingQuestion(false); setSelectedPreset(""); setNewAnswer(""); }}
                                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white/50"
                                    style={{ background: "rgba(255,255,255,0.08)" }}
                                >
                                    Отмена
                                </button>
                                <button
                                    onClick={addNewAnswer}
                                    disabled={!selectedPreset || !newAnswer.trim() || questionsSaving}
                                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
                                    style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)", opacity: (!selectedPreset || !newAnswer.trim()) ? 0.4 : 1 }}
                                >
                                    {questionsSaving ? "Сохраняем..." : "Добавить"}
                                </button>
                            </div>
                        </div>
                    ) : (
                        answers.length < PRESET_QUESTIONS.length && (
                            <button
                                onClick={() => setAddingQuestion(true)}
                                className="w-full py-3 rounded-2xl text-sm font-semibold transition-all active:scale-95"
                                style={{ background: "rgba(124,58,237,0.15)", border: "1.5px dashed rgba(124,58,237,0.4)", color: "#c084fc" }}
                            >
                                + Добавить ответ на вопрос
                            </button>
                        )
                    )}
                </div>
            )}

            {/* ── TAB: AI Анкета ── */}
            {tab === "ai" && (
                <div className="px-4 pt-3 space-y-4">
                    <div className="rounded-2xl p-5 text-center" style={{ background: "linear-gradient(135deg, rgba(124,58,237,0.15), rgba(79,70,229,0.1))", border: "1px solid rgba(124,58,237,0.25)" }}>
                        <div className="text-5xl mb-3">🤖</div>
                        <h2 className="text-base font-bold text-white mb-2">AI Настройка анкеты</h2>
                        <p className="text-sm text-white/60 leading-relaxed">
                            Наш AI проанализирует твой профиль и предложит улучшения описания, чтобы привлечь больше совпадений
                        </p>
                    </div>

                    <div className="space-y-3">
                        <div className="rounded-2xl p-4 flex items-start gap-3" style={{ background: "rgba(255,255,255,0.05)" }}>
                            <span className="text-xl flex-shrink-0">✨</span>
                            <div>
                                <p className="text-sm font-semibold text-white mb-1">Улучшение описания</p>
                                <p className="text-xs text-white/50">AI сделает твой текст «О себе» более привлекательным и живым</p>
                            </div>
                        </div>
                        <div className="rounded-2xl p-4 flex items-start gap-3" style={{ background: "rgba(255,255,255,0.05)" }}>
                            <span className="text-xl flex-shrink-0">🎯</span>
                            <div>
                                <p className="text-sm font-semibold text-white mb-1">Советы по профилю</p>
                                <p className="text-xs text-white/50">Рекомендации что добавить чтобы получать больше лайков</p>
                            </div>
                        </div>
                        <div className="rounded-2xl p-4 flex items-start gap-3" style={{ background: "rgba(255,255,255,0.05)" }}>
                            <span className="text-xl flex-shrink-0">📸</span>
                            <div>
                                <p className="text-sm font-semibold text-white mb-1">Подсказки по фото</p>
                                <p className="text-xs text-white/50">Советы какие фото работают лучше всего для привлечения внимания</p>
                            </div>
                        </div>
                    </div>

                    <div className="rounded-2xl p-4" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                        <p className="text-xs text-white/40 text-center">
                            💎 Функция AI Настройки доступна пользователям с подпиской <b className="text-purple-300">Premium</b> и <b className="text-amber-300">VIP</b>
                        </p>
                    </div>

                    <button
                        onClick={() => router.push(`/users/${userId}/premium`)}
                        className="w-full py-3.5 rounded-2xl text-sm font-bold text-white transition-all active:scale-95"
                        style={{ background: "linear-gradient(135deg, #7c3aed, #a855f7)" }}
                    >
                        🚀 Получить Premium
                    </button>
                </div>
            )}
        </div>
    );
}
