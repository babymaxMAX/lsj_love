"use client";
import { useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { BackEnd_URL } from "@/config/url";

export default function AppViewProfilePage() {
  const router = useRouter();
  const params = useParams();
  const { userId, loading: authLoading } = useAuth();
  const targetId = params?.targetId as string;

  useEffect(() => {
    if (!authLoading && !userId) router.replace("/app/login");
  }, [userId, authLoading, router]);

  if (!userId && !authLoading) return null;
  if (!targetId) return null;

  return (
    <div className="min-h-screen pb-8" style={{ background: "#0f0f1a", color: "#fff" }}>
      <div className="p-4">
        <button onClick={() => router.back()} className="text-white/60 mb-4">← Назад</button>
        <a href={`/users/${userId}/view-profile/${targetId}`} className="text-purple-400 underline">
          Открыть профиль (legacy)
        </a>
      </div>
    </div>
  );
}
