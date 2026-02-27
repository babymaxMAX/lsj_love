"use client";
import { useState } from "react";
import { BackEnd_URL } from "@/config/url";

interface Question {
    question_id: string;
    text: string;
    type: "multiple_choice" | "open";
    options: string[];
    category: string;
    emoji: string;
}

interface QuestionCardProps {
    question: Question;
    userId: string;
    onDone: () => void;
}

export function QuestionCard({ question, userId, onDone }: QuestionCardProps) {
    const [selected, setSelected] = useState<string[]>([]);
    const [customAnswer, setCustomAnswer] = useState("");
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const toggleOption = (opt: string) => {
        setSelected((prev) =>
            prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]
        );
    };

    const handleSave = async () => {
        const answer = question.type === "open"
            ? customAnswer.trim()
            : selected.length === 1 ? selected[0] : selected;
        if (!answer || (Array.isArray(answer) && !answer.length)) return;

        setSaving(true);
        try {
            await fetch(`${BackEnd_URL}/api/v1/profile/answers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    telegram_id: parseInt(userId),
                    question_id: question.question_id,
                    answer,
                }),
            });
            setSaved(true);
            setTimeout(onDone, 1200);
        } catch {
            setSaving(false);
        }
    };

    if (saved) {
        return (
            <div className="w-full max-w-sm">
                <div
                    className="rounded-3xl p-6 flex flex-col items-center justify-center gap-3"
                    style={{
                        background: "linear-gradient(135deg, rgba(124,58,237,0.3), rgba(219,39,119,0.2))",
                        border: "1.5px solid rgba(124,58,237,0.4)",
                        minHeight: 300,
                    }}
                >
                    <div className="text-5xl animate-bounce">✓</div>
                    <p className="text-white font-semibold text-lg">Сохранено!</p>
                    <p className="text-white/50 text-sm">Продолжаем смотреть анкеты</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full max-w-sm">
            <div
                className="rounded-3xl p-5 flex flex-col gap-4"
                style={{
                    background: "linear-gradient(135deg, rgba(124,58,237,0.2), rgba(219,39,119,0.15))",
                    border: "1.5px solid rgba(124,58,237,0.35)",
                    minHeight: 300,
                }}
            >
                <div className="text-center">
                    <div className="text-3xl mb-2">{question.emoji}</div>
                    <p className="text-white font-bold text-base">{question.text}</p>
                    <p className="text-white/40 text-xs mt-1">Расскажи о себе</p>
                </div>

                {question.type === "multiple_choice" ? (
                    <div className="flex flex-wrap gap-2 justify-center">
                        {question.options.map((opt) => (
                            <button
                                key={opt}
                                onClick={() => toggleOption(opt)}
                                className="px-4 py-2 rounded-full text-sm font-medium transition-all active:scale-95"
                                style={{
                                    background: selected.includes(opt)
                                        ? "linear-gradient(135deg, #7c3aed, #db2777)"
                                        : "rgba(255,255,255,0.1)",
                                    border: selected.includes(opt)
                                        ? "1px solid rgba(124,58,237,0.6)"
                                        : "1px solid rgba(255,255,255,0.15)",
                                    color: "#fff",
                                }}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                ) : (
                    <input
                        type="text"
                        value={customAnswer}
                        onChange={(e) => setCustomAnswer(e.target.value)}
                        placeholder="Напиши свой ответ..."
                        className="w-full px-4 py-3 rounded-2xl text-sm text-white placeholder-white/30 outline-none"
                        style={{
                            background: "rgba(255,255,255,0.08)",
                            border: "1px solid rgba(255,255,255,0.15)",
                        }}
                    />
                )}

                <div className="flex gap-2">
                    <button
                        onClick={onDone}
                        className="flex-1 py-3 rounded-2xl text-sm font-medium text-white/50"
                        style={{ background: "rgba(255,255,255,0.05)" }}
                    >
                        Пропустить
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving || (question.type === "open" ? !customAnswer.trim() : !selected.length)}
                        className="flex-1 py-3 rounded-2xl text-sm font-semibold text-white transition-all active:scale-95"
                        style={{
                            background: (question.type === "open" ? customAnswer.trim() : selected.length)
                                ? "linear-gradient(135deg, #7c3aed, #db2777)"
                                : "rgba(255,255,255,0.1)",
                            opacity: saving ? 0.6 : 1,
                        }}
                    >
                        {saving ? "⏳" : "Сохранить"}
                    </button>
                </div>
            </div>
        </div>
    );
}
