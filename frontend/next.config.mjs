/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://8.233.79.240",
    NEXT_PUBLIC_NATS_SSE_URL: process.env.NEXT_PUBLIC_NATS_SSE_URL || "https://8.233.79.240/events/stream",
    NEXT_PUBLIC_DEMO: process.env.NEXT_PUBLIC_DEMO || "false",
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${process.env.NEXT_PUBLIC_API_URL || "https://8.233.79.240"}/:path*` },
    ];
  },
};
export default nextConfig;
