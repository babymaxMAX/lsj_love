"use client";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";

export default function AppLoginPage() {
  const router = useRouter();
  const { error, clearError } = useAuth();

  const handleRetry = () => {
    clearError();
    router.push("/app");
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6"
      style={{ background: "#0f0f1a", color: "#fff" }}
    >
      <div className="text-6xl mb-6">🌐</div>
      <h1 className="text-xl font-bold mb-4 text-center">Вход на сайт</h1>
      {error ? (
        <>
          <p
            className="text-center mb-6 max-w-sm px-4 py-3 rounded-xl"
            style={{ background: "rgba(239,68,68,0.2)", color: "#fca5a5" }}
          >
            Не удалось выполнить вход. Попробуйте получить новую ссылку в боте.
          </p>
          <p className="text-sm text-white/40 mb-6 max-w-sm text-center">{error}</p>
        </>
      ) : (
        <p className="text-center text-white/60 mb-8 max-w-sm">
          Открой бота в Telegram, нажми «Открыть сайт» в профиле — и получишь ссылку для входа.
        </p>
      )}
      <button
        onClick={handleRetry}
        className="px-6 py-3 rounded-2xl font-semibold"
        style={{ background: "linear-gradient(135deg, #7c3aed, #ec4899)" }}
      >
        {error ? "Получить новую ссылку в боте" : "Уже есть ссылка? Попробовать снова"}
      </button>
    </div>
  );
}
