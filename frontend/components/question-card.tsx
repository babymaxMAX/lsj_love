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

type Step = "answering" | "reformulating" | "picking" | "saving" | "saved";

export function QuestionCard({ question, userId, onDone }: QuestionCardProps) {
    const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
    const [customAnswer, setCustomAnswer] = useState("");
    const [step, setStep] = useState<Step>("answering");
    const [variants, setVariants] = useState<string[]>([]);
    const [pickedVariant, setPickedVariant] = useState<string | null>(null);
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

    const fetchVariants = async (answer: string) => {
        setStep("reformulating");
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/profile/reformulate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: question.text, answer }),
            });
            const data = await res.json();
            const v = data.variants || [answer];
            setVariants(v);
            setPickedVariant(null);
            setStep("picking");
        } catch {
            setVariants([answer]);
            setStep("picking");
        }
    };

    const submitForReformulation = async () => {
        const raw = getRawAnswer();
        if (!raw) return;
        setRawAnswer(raw);
        await fetchVariants(raw);
    };

    const regenerate = async () => {
        await fetchVariants(rawAnswer);
    };

    const saveAnswer = async () => {
        if (!pickedVariant) return;
        setStep("saving");
        try {
            await fetch(`${BackEnd_URL}/api/v1/profile/answers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    telegram_id: parseInt(userId),
                    question_id: question.question_id,
                    answer: pickedVariant,
                }),
            });
            setStep("saved");
            setTimeout(onDone, 800);
        } catch {
            setStep("picking");
        }
    };

    const cardStyle = {
        borderRadius: 24,
        background: "linear-gradient(135deg, #7c3aed 0%, #db2777 100%)",
        padding: "28px 20px",
        minHeight: 320,
        display: "flex" as const,
        flexDirection: "column" as const,
        alignItems: "center" as const,
        justifyContent: "center" as const,
        gap: 16,
        boxShadow: "0 8px 32px rgba(124,58,237,0.4)",
    };

    if (step === "saved") {
        return (
            <div className="w-full max-w-sm">
                <div style={cardStyle}>
                    <div style={{ fontSize: 56 }}>✓</div>
                    <div style={{ fontSize: 20, fontWeight: 800, color: "#fff" }}>Сохранено в профиль!</div>
                    <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)" }}>Продолжаем смотреть анкеты</div>
                </div>
            </div>
        );
    }

    if (step === "reformulating") {
        return (
            <div className="w-full max-w-sm">
                <div style={cardStyle}>
                    <div style={{ fontSize: 42 }}>✨</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#fff", textAlign: "center" }}>
                        AI подбирает формулировки...
                    </div>
                    <div style={{ display: "flex", gap: 4 }}>
                        {[0, 1, 2].map((i) => (
                            <div
                                key={i}
                                className="animate-bounce"
                                style={{
                                    width: 8, height: 8, borderRadius: "50%",
                                    background: "#fff", opacity: 0.7,
                                    animationDelay: `${i * 0.15}s`,
                                }}
                            />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (step === "picking" || step === "saving") {
        return (
            <div className="w-full max-w-sm">
                <div style={cardStyle}>
                    <div style={{ fontSize: 14, color: "rgba(255,255,255,0.7)", textAlign: "center" }}>
                        ✨ Выбери формулировку для профиля:
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%" }}>
                        {variants.map((v, i) => (
                            <button
                                key={i}
                                onClick={() => setPickedVariant(v)}
                                style={{
                                    padding: "14px 16px", borderRadius: 16, textAlign: "left",
                                    fontSize: 15, fontWeight: 600, lineHeight: 1.3,
                                    background: pickedVariant === v ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.08)",
                                    border: pickedVariant === v ? "2px solid #fff" : "2px solid rgba(255,255,255,0.2)",
                                    color: "#fff", cursor: "pointer", transition: "all 0.15s",
                                }}
                            >
                                {v}
                            </button>
                        ))}
                    </div>

                    <div style={{ display: "flex", gap: 8, width: "100%" }}>
                        <button
                            onClick={regenerate}
                            disabled={step === "saving"}
                            style={{
                                flex: 1, padding: "12px", borderRadius: 16,
                                background: "rgba(255,255,255,0.12)", color: "#fff",
                                fontWeight: 600, fontSize: 13, border: "none", cursor: "pointer",
                            }}
                        >
                            🔄 Ещё варианты
                        </button>
                        <button
                            onClick={saveAnswer}
                            disabled={!pickedVariant || step === "saving"}
                            style={{
                                flex: 1, padding: "12px", borderRadius: 16,
                                background: pickedVariant ? "#fff" : "rgba(255,255,255,0.15)",
                                color: pickedVariant ? "#7c3aed" : "rgba(255,255,255,0.4)",
                                fontWeight: 800, fontSize: 14, border: "none",
                                cursor: pickedVariant ? "pointer" : "default",
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
                <div style={{ fontSize: 42 }}>{question.emoji}</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#fff", textAlign: "center", lineHeight: 1.3 }}>
                    {question.text}
                </div>

                {question.type === "multiple_choice" && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
                        {question.options.map((option, i) => (
                            <button
                                key={i}
                                onClick={() => toggleOption(option)}
                                style={{
                                    padding: "9px 16px", borderRadius: 100,
                                    border: selectedOptions.includes(option) ? "2px solid #fff" : "2px solid rgba(255,255,255,0.3)",
                                    background: selectedOptions.includes(option) ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.08)",
                                    color: "#fff", fontWeight: 600, fontSize: 13, cursor: "pointer", transition: "all 0.15s",
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
                        width: "100%", padding: "11px 14px", borderRadius: 14,
                        border: "1.5px solid rgba(255,255,255,0.3)", background: "rgba(255,255,255,0.1)",
                        color: "#fff", fontSize: 14, outline: "none",
                    }}
                />

                {hasAnswer && (
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", textAlign: "center" }}>
                        ✨ AI предложит 3 варианта красивой формулировки для профиля
                    </div>
                )}

                <div style={{ display: "flex", gap: 8, width: "100%" }}>
                    <button
                        onClick={onDone}
                        style={{
                            flex: 1, padding: "13px", borderRadius: 16,
                            background: "rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.7)",
                            fontWeight: 600, fontSize: 14, border: "none", cursor: "pointer",
                        }}
                    >
                        Пропустить
                    </button>
                    <button
                        onClick={submitForReformulation}
                        disabled={!hasAnswer}
                        style={{
                            flex: 1, padding: "13px", borderRadius: 16,
                            background: hasAnswer ? "#fff" : "rgba(255,255,255,0.15)",
                            color: hasAnswer ? "#7c3aed" : "rgba(255,255,255,0.4)",
                            fontWeight: 800, fontSize: 15, border: "none",
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
