/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    typescript: {
        ignoreBuildErrors: true,
    },
    eslint: {
        ignoreDuringBuilds: true,
    },
    optimizeFonts: false,
    env: {
        BACKEND_URL: process.env.BACKEND_URL || "https://lsjlove.duckdns.org",
    },
    images: {
        remotePatterns: [
            { protocol: "https", hostname: "**" },
        ],
    },
    async headers() {
        return [
            {
                source: "/(.*)",
                headers: [
                    { key: "X-Frame-Options", value: "SAMEORIGIN" },
                    { key: "X-Content-Type-Options", value: "nosniff" },
                ],
            },
        ];
    },
};

module.exports = nextConfig;
