"use client";
import { useState } from "react";
import { BackEnd_URL } from "@/config/url";

interface PhotoLikeButtonProps {
    ownerId: number;
    photoIndex: number;
    viewerId: number;
    initialLikes: number;
    initialLiked: boolean;
}

export function PhotoLikeButton({ ownerId, photoIndex, viewerId, initialLikes, initialLiked }: PhotoLikeButtonProps) {
    const [liked, setLiked] = useState(initialLiked);
    const [count, setCount] = useState(initialLikes);
    const [loading, setLoading] = useState(false);

    const toggle = async () => {
        if (loading || viewerId === ownerId) return;
        setLoading(true);
        setLiked((l) => !l);
        setCount((c) => (liked ? c - 1 : c + 1));
        try {
            const res = await fetch(`${BackEnd_URL}/api/v1/photo-interactions/likes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ from_user: viewerId, owner_id: ownerId, photo_index: photoIndex }),
            });
            if (res.ok) {
                const data = await res.json();
                setLiked(data.liked);
                setCount(data.count);
            }
        } catch {
            setLiked((l) => !l);
            setCount((c) => (liked ? c + 1 : c - 1));
        }
        setLoading(false);
    };

    const isSelf = viewerId === ownerId;

    return (
        <button
            onClick={toggle}
            disabled={isSelf}
            style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                background: liked ? "rgba(239,68,68,0.2)" : "rgba(255,255,255,0.1)",
                border: liked ? "1px solid rgba(239,68,68,0.5)" : "1px solid rgba(255,255,255,0.2)",
                borderRadius: 100,
                padding: "6px 12px",
                color: liked ? "#ef4444" : "#fff",
                fontSize: 13,
                fontWeight: 600,
                cursor: isSelf ? "default" : "pointer",
                backdropFilter: "blur(8px)",
                transition: "all 0.2s",
                opacity: isSelf ? 0.5 : 1,
            }}
        >
            <span style={{ fontSize: 16 }}>{liked ? "❤️" : "🤍"}</span>
            {count > 0 && <span>{count}</span>}
        </button>
    );
}
