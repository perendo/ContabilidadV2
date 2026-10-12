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
  async redirects() {
    // Redirección a nivel de configuración (no un `redirect()` de Server
    // Component). Un `redirect()` ejecutado durante una navegación cliente en el
    // App Router dispara el bug de Next "Rendered more hooks than during the
    // previous render" (vercel/next.js#63121). Aquí `/banco` se resuelve antes
    // de renderizar React, por lo que la navegación cliente funciona.
    return [{ source: "/banco", destination: "/banco/importar", permanent: false }];
  },
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
