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
				<Providers themeProps={{ attribute: "class", defaultTheme: "dark" }}>
					<main className="max-w-lg mx-auto min-h-screen">
						{children}
					</main>
				</Providers>
			</body>
		</html>
	);
}
