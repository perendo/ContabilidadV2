/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    "@mui/material",
    "@mui/system",
    "@mui/icons-material",
    "@emotion/react",
    "@emotion/styled",
    "@mui/material-nextjs",
  ],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
