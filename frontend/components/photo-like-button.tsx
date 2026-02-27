"use client";
import { useState, useEffect } from "react";
import { BackEnd_URL } from "@/config/url";

interface PhotoLikeButtonProps {
    ownerId: number;
    photoIndex: number;
    viewerId: number;
    initialLikes?: number;
    initialLiked?: boolean;
}

export function PhotoLikeButton({ ownerId, photoIndex, viewerId, initialLikes, initialLiked }: PhotoLikeButtonProps) {
    const [liked, setLiked] = useState(initialLiked ?? false);
    const [count, setCount] = useState(initialLikes ?? 0);
    const [loading, setLoading] = useState(false);
    const [fetched, setFetched] = useState(initialLikes !== undefined);

    useEffect(() => {
        if (fetched) return;
        fetch(`${BackEnd_URL}/api/v1/photo-interactions/likes/${ownerId}/${photoIndex}?viewer_id=${viewerId}`)
            .then((r) => r.ok ? r.json() : null)
            .then((d) => {
                if (d) {
                    setCount(d.count ?? 0);
                    setLiked(d.liked_by_me ?? false);
                }
                setFetched(true);
            })
            .catch(() => setFetched(true));
    }, [ownerId, photoIndex, viewerId, fetched]);

    useEffect(() => {
        setFetched(false);
    }, [photoIndex]);

    const toggle = async () => {
        if (loading || viewerId === ownerId) return;
        setLoading(true);
        const prevLiked = liked;
        const prevCount = count;
        setLiked(!prevLiked);
        setCount(prevLiked ? prevCount - 1 : prevCount + 1);
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
            setLiked(prevLiked);
            setCount(prevCount);
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
