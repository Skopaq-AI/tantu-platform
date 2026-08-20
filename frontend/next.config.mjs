/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_NATS_SSE_URL: process.env.NEXT_PUBLIC_NATS_SSE_URL || "http://localhost:8000/events/stream",
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*` },
    ];
  },
};
export default nextConfig;
