"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { meBestResult, meLike, meDislike } from "@/lib/api";
import { SwipeCard } from "@/components/swipe-card";
import { BottomNavApp } from "@/components/bottom-nav-app";

export default function AppPage() {
  const router = useRouter();
  const userId = useCurrentUser();
  const [users, setUsers] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [seenIds] = useState<Set<number>>(() => new Set());
  const [likeError, setLikeError] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const data = await meBestResult();
      const fresh = (data.items || []).filter((u: any) => !seenIds.has(u.telegram_id));
      setUsers(fresh);
      setCurrentIndex(0);
    } catch {
      setUsers([]);
    }
    setLoading(false);
  }, [userId, seenIds]);

  useEffect(() => {
    if (!authLoading && !userId) {
      router.replace("/app/login");
      return;
    }
    if (userId) loadUsers();
  }, [userId, authLoading, loadUsers, router]);

  const handleLike = async (targetId: number) => {
    seenIds.add(targetId);
    setLikeError(null);
    try {
      await meLike(targetId);
    } catch (e) {
      setLikeError(String(e));
      setTimeout(() => setLikeError(null), 5000);
      return;
    }
    setCurrentIndex((i) => i + 1);
  };

  const handleDislike = async (targetId: number) => {
    seenIds.add(targetId);
    try {
      await meDislike(targetId);
    } catch {
      /* ignore */
    }
    setCurrentIndex((i) => i + 1);
  };

  const currentUser = users[currentIndex];

  if (!userId && !authLoading) return null;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0f0f1a" }}>
        <div className="text-center text-white/50">Ищем людей рядом...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen pb-20" style={{ background: "#0f0f1a", color: "#fff" }}>
      <div
        className="flex items-center justify-center px-4 py-3 flex-shrink-0"
        style={{ background: "#18182a", borderBottom: "1px solid rgba(255,255,255,0.08)" }}
      >
        <h1 className="text-base font-bold">Kupidon AI 💕</h1>
      </div>
      {likeError && (
        <div
          style={{
            position: "fixed",
            top: 70,
            left: "50%",
            transform: "translateX(-50%)",
            background: "#7c3aed",
            color: "#fff",
            borderRadius: 12,
            padding: "10px 20px",
            fontSize: 13,
            zIndex: 100,
          }}
        >
          ❤️ {likeError}
        </div>
      )}
      <div className="flex-1 flex items-center justify-center px-4 py-6">
        {currentUser ? (
          <SwipeCard
            user={currentUser}
            userId={userId}
            onLike={() => handleLike(currentUser.telegram_id)}
            onDislike={() => handleDislike(currentUser.telegram_id)}
          />
        ) : (
          <div className="text-center px-8">
            <div className="text-6xl mb-6">😔</div>
            <h2 className="text-xl font-semibold mb-2">Анкеты закончились</h2>
            <p className="text-sm mb-4 text-white/50">Возвращайся позже — появятся новые!</p>
            <button
              onClick={loadUsers}
              className="px-6 py-3 rounded-2xl font-semibold"
              style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
            >
              🔄 Обновить
            </button>
          </div>
        )}
      </div>
      <BottomNavApp userId={userId} />
    </div>
  );
}
