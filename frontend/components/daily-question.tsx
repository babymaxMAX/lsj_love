"use client";
import { useState } from "react";

interface DailyQuestionProps {
    question: string;
    userId: string;
    onClose: () => void;
}

export function DailyQuestion({ question, userId, onClose }: DailyQuestionProps) {
    const [answer, setAnswer] = useState("");
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = () => {
        if (answer.trim()) {
            setSubmitted(true);
            setTimeout(onClose, 2000);
        }
    };

    return (
        <div className="mx-4 mb-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-2xl p-4">
            <div className="flex justify-between items-start mb-3">
                <h3 className="font-semibold text-sm">💬 Вопрос дня</h3>
                <button onClick={onClose} className="text-default-400 hover:text-default-600 text-lg leading-none">
                    ×
                </button>
            </div>
            <p className="text-default-700 text-sm mb-3">{question}</p>
            {!submitted ? (
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        placeholder="Твой ответ..."
                        className="flex-1 bg-content1 rounded-xl px-3 py-2 text-sm outline-none border border-divider focus:border-primary"
                        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    />
                    <button
                        onClick={handleSubmit}
                        disabled={!answer.trim()}
                        className="px-3 py-2 bg-primary text-white rounded-xl text-sm disabled:opacity-50"
                    >
                        ✓
                    </button>
                </div>
            ) : (
                <p className="text-green-500 text-sm font-medium">
                    ✅ Ответ записан! Совпадение покажем в матчах.
                </p>
            )}
        </div>
    );
}
