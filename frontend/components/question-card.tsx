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

type Step = "answering" | "reformulating" | "confirming" | "saving" | "saved";

export function QuestionCard({ question, userId, onDone }: QuestionCardProps) {
    const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
    const [customAnswer, setCustomAnswer] = useState("");
    const [step, setStep] = useState<Step>("answering");
    const [formatted, setFormatted] = useState("");
    const [rawAnswer, setRawAnswer] = useState("");

    const toggleOption = (opt: string) => {
        setSelectedOptions((prev) =>
            prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]
        );
    };

    const getRawAnswer = (): string => {
        if (question.type === "open") return customAnswer.trim();
        const parts = [...selectedOptions];
        if (customAnswer.trim()) parts.push(customAnswer.trim());
        return parts.join(", ");
    };

    const submitForReformulation = async () => {
        const raw = getRawAnswer();
        if (!raw) return;
        setRawAnswer(raw);
        setStep("reformulating");

        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/profile/reformulate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: question.text, answer: raw }),
            });
            const data = await res.json();
            setFormatted(data.formatted || raw);
            setStep("confirming");
        } catch {
            setFormatted(raw);
            setStep("confirming");
        }
    };

    const reReformulate = async () => {
        setStep("reformulating");
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/profile/reformulate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: question.text, answer: rawAnswer }),
            });
            const data = await res.json();
            setFormatted(data.formatted || rawAnswer);
            setStep("confirming");
        } catch {
            setStep("confirming");
        }
    };

    const saveFormatted = async () => {
        setStep("saving");
        try {
            await fetch(`${BackEnd_URL}/api/v1/profile/answers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    telegram_id: parseInt(userId),
                    question_id: question.question_id,
                    answer: formatted,
                }),
            });
            setStep("saved");
            setTimeout(onDone, 800);
        } catch {
            setStep("confirming");
        }
    };

    const cardStyle = {
        borderRadius: 24,
        background: "linear-gradient(135deg, #7c3aed 0%, #db2777 100%)",
        padding: "32px 24px",
        minHeight: 350,
        display: "flex" as const,
        flexDirection: "column" as const,
        alignItems: "center" as const,
        justifyContent: "center" as const,
        gap: 20,
        boxShadow: "0 8px 32px rgba(124,58,237,0.4)",
    };

    if (step === "saved") {
        return (
            <div className="w-full max-w-sm">
                <div style={cardStyle}>
                    <div style={{ fontSize: 64 }}>✓</div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#fff" }}>Сохранено!</div>
                    <div style={{ fontSize: 14, color: "rgba(255,255,255,0.7)" }}>Продолжаем смотреть анкеты</div>
                </div>
            </div>
        );
    }

    if (step === "reformulating") {
        return (
            <div className="w-full max-w-sm">
                <div style={cardStyle}>
                    <div style={{ fontSize: 48 }}>✨</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#fff", textAlign: "center" }}>
                        AI формулирует ответ...
                    </div>
                    <div style={{ display: "flex", gap: 4 }}>
                        {[0, 1, 2].map((i) => (
                            <div
                                key={i}
                                style={{
                                    width: 8, height: 8, borderRadius: "50%",
                                    background: "#fff", opacity: 0.7,
                                    animation: "bounce 0.6s infinite",
                                    animationDelay: `${i * 0.15}s`,
                                }}
                            />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (step === "confirming" || step === "saving") {
        return (
            <div className="w-full max-w-sm">
                <div style={cardStyle}>
                    <div style={{ fontSize: 36 }}>✨</div>
                    <div style={{ fontSize: 14, color: "rgba(255,255,255,0.7)", textAlign: "center" }}>
                        AI сформулировал твой ответ:
                    </div>
                    <div style={{
                        fontSize: 20, fontWeight: 800, color: "#fff", textAlign: "center",
                        padding: "16px 20px", background: "rgba(255,255,255,0.15)",
                        borderRadius: 16, border: "1px solid rgba(255,255,255,0.3)",
                        lineHeight: 1.4,
                    }}>
                        "{formatted}"
                    </div>
                    <div style={{ display: "flex", gap: 10, width: "100%" }}>
                        <button
                            onClick={reReformulate}
                            disabled={step === "saving"}
                            style={{
                                flex: 1, padding: "14px", borderRadius: 18,
                                background: "rgba(255,255,255,0.15)", color: "#fff",
                                fontWeight: 600, fontSize: 14, border: "none", cursor: "pointer",
                            }}
                        >
                            🔄 Другой
                        </button>
                        <button
                            onClick={saveFormatted}
                            disabled={step === "saving"}
                            style={{
                                flex: 1, padding: "14px", borderRadius: 18,
                                background: "#fff", color: "#7c3aed",
                                fontWeight: 800, fontSize: 15, border: "none", cursor: "pointer",
                                opacity: step === "saving" ? 0.6 : 1,
                            }}
                        >
                            {step === "saving" ? "⏳" : "👍 Сохранить"}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const hasAnswer = question.type === "open"
        ? customAnswer.trim().length > 0
        : selectedOptions.length > 0 || customAnswer.trim().length > 0;

    return (
        <div className="w-full max-w-sm">
            <div style={cardStyle}>
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
                                    padding: "10px 18px", borderRadius: 100,
                                    border: selectedOptions.includes(option) ? "2px solid #fff" : "2px solid rgba(255,255,255,0.3)",
                                    background: selectedOptions.includes(option) ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.08)",
                                    color: "#fff", fontWeight: 600, fontSize: 14, cursor: "pointer", transition: "all 0.15s",
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
                        width: "100%", padding: "12px 16px", borderRadius: 16,
                        border: "1.5px solid rgba(255,255,255,0.3)", background: "rgba(255,255,255,0.1)",
                        color: "#fff", fontSize: 15, outline: "none",
                    }}
                />

                {hasAnswer && (
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", textAlign: "center" }}>
                        ✨ AI сформулирует твой ответ красиво для профиля
                    </div>
                )}

                <div style={{ display: "flex", gap: 10, width: "100%" }}>
                    <button
                        onClick={onDone}
                        style={{
                            flex: 1, padding: "14px", borderRadius: 18,
                            background: "rgba(255,255,255,0.15)", color: "rgba(255,255,255,0.7)",
                            fontWeight: 600, fontSize: 15, border: "none", cursor: "pointer",
                        }}
                    >
                        Пропустить
                    </button>
                    <button
                        onClick={submitForReformulation}
                        disabled={!hasAnswer}
                        style={{
                            flex: 1, padding: "14px", borderRadius: 18,
                            background: hasAnswer ? "#fff" : "rgba(255,255,255,0.2)",
                            color: hasAnswer ? "#7c3aed" : "rgba(255,255,255,0.4)",
                            fontWeight: 800, fontSize: 16, border: "none",
                            cursor: hasAnswer ? "pointer" : "default",
                        }}
                    >
                        Ответить ✓
                    </button>
                </div>
            </div>
        </div>
    );
}
