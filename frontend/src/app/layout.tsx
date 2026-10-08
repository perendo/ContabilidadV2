import type { Metadata } from "next";

import Providers from "./Providers";

export const metadata: Metadata = {
  title: "ContabilidadV2",
  description: "Módulo core contable multi-tenant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}