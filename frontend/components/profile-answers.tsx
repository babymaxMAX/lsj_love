"use client";
import { useEffect, useState } from "react";
import { BackEnd_URL } from "@/config/url";

interface Answer {
    question_id: string;
    text: string;
    emoji: string;
    category: string;
    answer: string | string[];
}

const CATEGORY_LABELS: Record<string, string> = {
    lifestyle: "Образ жизни",
    personality: "Личность",
    values: "Ценности",
    hobbies: "Хобби",
};

export function ProfileAnswers({ userId }: { userId: string }) {
    const [answers, setAnswers] = useState<Answer[]>([]);

    useEffect(() => {
        fetch(`${BackEnd_URL}/api/v1/profile/answers/${userId}`)
            .then((r) => r.json())
            .then((d) => setAnswers(d.answers || []))
            .catch(() => {});
    }, [userId]);

    if (!answers.length) return null;

    const grouped = answers.reduce<Record<string, Answer[]>>((acc, a) => {
        (acc[a.category] = acc[a.category] || []).push(a);
        return acc;
    }, {});

    return (
        <div className="rounded-2xl p-4 space-y-3" style={{ background: "rgba(255,255,255,0.06)" }}>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4, color: "#fff" }}>Обо мне</div>
            {Object.entries(grouped).map(([cat, items]) => (
                <div key={cat}>
                    <p className="text-xs text-white/30 mb-1.5">{CATEGORY_LABELS[cat] || cat}</p>
                    <div className="flex flex-wrap gap-1.5">
                        {items.map((a) => {
                            const val = Array.isArray(a.answer) ? a.answer.join(", ") : a.answer;
                            return (
                                <span
                                    key={a.question_id}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium"
                                    style={{
                                        background: "rgba(124,58,237,0.15)",
                                        border: "1px solid rgba(124,58,237,0.25)",
                                        color: "rgba(255,255,255,0.8)",
                                    }}
                                >
                                    <span>{a.emoji}</span>
                                    <span>{val}</span>
                                </span>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
}
