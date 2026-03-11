"use client";
import { useRouter } from "next/navigation";

export default function AppLoginPage() {
  const router = useRouter();

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6"
      style={{ background: "#0f0f1a", color: "#fff" }}
    >
      <div className="text-6xl mb-6">🌐</div>
      <h1 className="text-xl font-bold mb-4 text-center">Вход на сайт</h1>
      <p className="text-center text-white/60 mb-8 max-w-sm">
        Открой бота в Telegram, нажми «Открыть сайт» в профиле — и получишь ссылку для входа.
      </p>
      <button
        onClick={() => router.push("/app")}
        className="px-6 py-3 rounded-2xl font-semibold"
        style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
      >
        Уже есть ссылка? Попробовать снова
      </button>
    </div>
  );
}
