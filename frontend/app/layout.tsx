"use client";
import "@/styles/globals.css";
import { fontSans } from "@/config/fonts";
import { Providers } from "./providers";
import clsx from "clsx";
import Script from "next/script";

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<html lang="ru" suppressHydrationWarning>
			<head>
				<title>LSJLove — Знакомства в Telegram</title>
				<meta name="description" content="Знакомься, общайся и находи свою половинку прямо в Telegram" />
				<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
				<Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
			</head>
			<body
				className={clsx(
					"min-h-screen bg-background font-sans antialiased",
					fontSans.variable
				)}
			>
				<script dangerouslySetInnerHTML={{ __html: `
					document.addEventListener('gesturestart', function(e) { e.preventDefault(); }, { passive: false });
					document.addEventListener('gesturechange', function(e) { e.preventDefault(); }, { passive: false });
					document.addEventListener('gestureend', function(e) { e.preventDefault(); }, { passive: false });
					document.addEventListener('touchstart', function(e) {
						if (e.touches.length > 1) { e.preventDefault(); }
					}, { passive: false });
					(function() {
						function setSafeTop() {
							var tg = window.Telegram && window.Telegram.WebApp;
							var h = (tg && tg.viewportStableHeight && tg.headerColor) ? 0 : 0;
							var safe = (tg && tg.safeAreaInset) ? tg.safeAreaInset.top : 0;
							var total = Math.max(safe, 8);
							document.documentElement.style.setProperty('--safe-top', total + 'px');
						}
						setSafeTop();
						document.addEventListener('DOMContentLoaded', setSafeTop);
						if (window.Telegram && window.Telegram.WebApp) {
							window.Telegram.WebApp.onEvent('viewportChanged', setSafeTop);
						}
					})();
				`}} />
				<Providers themeProps={{ attribute: "class", defaultTheme: "dark" }}>
					<main className="max-w-lg mx-auto min-h-screen" style={{ paddingTop: 8 }}>
						{children}
					</main>
				</Providers>
			</body>
		</html>
	);
}
