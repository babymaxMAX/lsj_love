"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { BottomNavApp } from "@/components/bottom-nav-app";

export default function AppPremiumPage() {
  const router = useRouter();
  const { userId, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !userId) router.replace("/app/login");
  }, [userId, authLoading, router]);

  if (!userId && !authLoading) return null;

  return (
    <div className="flex flex-col min-h-screen pb-20" style={{ background: "#0f0f1a", color: "#fff" }}>
      <div className="px-4 py-6">
        <h1 className="text-lg font-bold">⭐ Premium</h1>
        <p className="text-sm text-white/5 mt-2">Подписки и пакеты</p>
        <a href={`/users/${userId}/premium`} className="text-purple-400 underline mt-4 block">
          Купить Premium (legacy)
        </a>
      </div>
      <BottomNavApp userId={userId || ""} />
    </div>
  );
}
