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
    const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
    const [customAnswer, setCustomAnswer] = useState("");
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const toggleOption = (opt: string) => {
        setSelectedOptions((prev) =>
            prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]
        );
    };

    const submitAnswer = async () => {
        let answer: string | string[];
        if (question.type === "open") {
            answer = customAnswer.trim();
        } else {
            const combined = [...selectedOptions];
            if (customAnswer.trim()) combined.push(customAnswer.trim());
            answer = combined.length === 1 ? combined[0] : combined;
        }
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
            setTimeout(onDone, 1000);
        } catch {
            setSaving(false);
        }
    };

    if (saved) {
        return (
            <div className="w-full max-w-sm">
                <div
                    style={{
                        borderRadius: 24,
                        background: "linear-gradient(135deg, #7c3aed 0%, #db2777 100%)",
                        padding: "40px 24px",
                        minHeight: 350,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 16,
                        boxShadow: "0 8px 32px rgba(124,58,237,0.4)",
                    }}
                >
                    <div style={{ fontSize: 64 }}>✓</div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#fff" }}>Сохранено!</div>
                    <div style={{ fontSize: 14, color: "rgba(255,255,255,0.7)" }}>Продолжаем смотреть анкеты</div>
                </div>
            </div>
        );
    }

    const hasAnswer = question.type === "open"
        ? customAnswer.trim().length > 0
        : selectedOptions.length > 0 || customAnswer.trim().length > 0;

    return (
        <div className="w-full max-w-sm">
            <div
                style={{
                    borderRadius: 24,
                    background: "linear-gradient(135deg, #7c3aed 0%, #db2777 100%)",
                    padding: "32px 24px",
                    minHeight: 350,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 20,
                    boxShadow: "0 8px 32px rgba(124,58,237,0.4)",
                }}
            >
                <div style={{ fontSize: 48 }}>{question.emoji}</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: "#fff", textAlign: "center", lineHeight: 1.3 }}>
                    {question.text}
                </div>

                {question.type === "multiple_choice" && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center" }}>
                        {question.options.map((option, i) => (
                            <button
                                key={i}
                                onClick={() => toggleOption(option)}
                                style={{
                                    padding: "10px 18px",
                                    borderRadius: 100,
                                    border: selectedOptions.includes(option)
                                        ? "2px solid #fff"
                                        : "2px solid rgba(255,255,255,0.3)",
                                    background: selectedOptions.includes(option)
                                        ? "rgba(255,255,255,0.25)"
                                        : "rgba(255,255,255,0.08)",
                                    color: "#fff",
                                    fontWeight: 600,
                                    fontSize: 14,
                                    cursor: "pointer",
                                    transition: "all 0.15s",
                                }}
                            >
                                {option}
                            </button>
                        ))}
                    </div>
                )}

                <input
                    placeholder="Свой вариант..."
                    value={customAnswer}
                    onChange={(e) => setCustomAnswer(e.target.value)}
                    style={{
                        width: "100%",
                        padding: "12px 16px",
                        borderRadius: 16,
                        border: "1.5px solid rgba(255,255,255,0.3)",
                        background: "rgba(255,255,255,0.1)",
                        color: "#fff",
                        fontSize: 15,
                        outline: "none",
                    }}
                />

                <div style={{ display: "flex", gap: 10, width: "100%" }}>
                    <button
                        onClick={onDone}
                        style={{
                            flex: 1,
                            padding: "14px",
                            borderRadius: 18,
                            background: "rgba(255,255,255,0.15)",
                            color: "rgba(255,255,255,0.7)",
                            fontWeight: 600,
                            fontSize: 15,
                            border: "none",
                            cursor: "pointer",
                        }}
                    >
                        Пропустить
                    </button>
                    <button
                        onClick={submitAnswer}
                        disabled={saving || !hasAnswer}
                        style={{
                            flex: 1,
                            padding: "14px",
                            borderRadius: 18,
                            background: hasAnswer ? "#fff" : "rgba(255,255,255,0.2)",
                            color: hasAnswer ? "#7c3aed" : "rgba(255,255,255,0.4)",
                            fontWeight: 800,
                            fontSize: 16,
                            border: "none",
                            cursor: hasAnswer ? "pointer" : "default",
                            opacity: saving ? 0.6 : 1,
                        }}
                    >
                        {saving ? "⏳" : "Ответить ✓"}
                    </button>
                </div>
            </div>
        </div>
    );
}
