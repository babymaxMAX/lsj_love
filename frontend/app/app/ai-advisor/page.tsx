"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { BottomNavApp } from "@/components/bottom-nav-app";

export default function AppAiAdvisorPage() {
  const router = useRouter();
  const { userId, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !userId) router.replace("/app/login");
  }, [userId, authLoading, router]);

  if (!userId && !authLoading) return null;

  return (
    <div className="flex flex-col min-h-screen pb-20" style={{ background: "#0f0f1a", color: "#fff" }}>
      <div className="px-4 py-6">
        <h1 className="text-lg font-bold">🧠 AI Чат</h1>
        <a href={`/users/${userId}/ai-advisor`} className="text-purple-400 underline mt-4 block">
          AI Советник (legacy)
        </a>
      </div>
      <BottomNavApp userId={userId || ""} />
    </div>
  );
}
