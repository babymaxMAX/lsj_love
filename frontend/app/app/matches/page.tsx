"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { meMatches } from "@/lib/api";
import { BottomNavApp } from "@/components/bottom-nav-app";
import { BackEnd_URL } from "@/config/url";

export default function AppMatchesPage() {
  const router = useRouter();
  const { userId, loading: authLoading } = useAuth();
  const [matches, setMatches] = useState<any[]>([]);
  const [botUsername, setBotUsername] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const data = await meMatches();
      setMatches(data.items || []);
      setBotUsername(data.bot_username || "");
    } catch {
      setMatches([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!authLoading && !userId) {
      router.replace("/app/login");
      return;
    }
    if (userId) fetchMatches();
  }, [userId, authLoading, fetchMatches, router]);

  const goToProfile = (targetId: number) => {
    router.push(`/app/view-profile/${targetId}`);
  };

  if (!userId && !authLoading) return null;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0f0f1a" }}>
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen pb-20" style={{ background: "#0f0f1a", color: "#fff" }}>
      <div className="px-4 pt-4 pb-2">
        <h1 className="text-lg font-bold">💌 Матчи</h1>
        <p className="text-xs mt-0.5 text-white/40">Взаимные симпатии</p>
      </div>
      <div className="flex-1 px-4 py-2 overflow-auto">
        {matches.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-5xl mb-4">💫</div>
            <p className="text-white/60">Пока нет матчей. Свайпай анкеты!</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {matches.map((u) => (
              <button
                key={u.telegram_id}
                onClick={() => goToProfile(u.telegram_id)}
                className="w-full flex items-center gap-4 p-4 rounded-2xl text-left transition-all active:scale-[0.98]"
                style={{ background: "rgba(255,255,255,0.06)" }}
              >
                <img
                  src={`${BackEnd_URL}/api/v1/users/${u.telegram_id}/photo/0`}
                  alt=""
                  className="w-16 h-16 rounded-full object-cover"
                />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold truncate">{u.name}</p>
                  <p className="text-sm text-white/5 truncate">{u.city || ""}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      <BottomNavApp userId={userId || ""} />
    </div>
  );
}
