"use client";
import { Suspense } from "react";
import { AuthProvider } from "@/context/auth-context";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<AppLoading />}>
      <AuthProvider>{children}</AuthProvider>
    </Suspense>
  );
}

function AppLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "#0f0f1a" }}>
      <div className="text-center text-white/50">Загрузка...</div>
    </div>
  );
}
