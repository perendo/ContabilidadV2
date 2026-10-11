"use client";

import { Tab, Tabs } from "@mui/material";
import { usePathname, useRouter } from "next/navigation";

const SECCIONES = [
  { id: "importar", label: "Importar extracto", href: "/banco/importar" },
  { id: "reglas", label: "Reglas", href: "/banco/reglas" },
  { id: "pendientes", label: "Pendientes", href: "/banco/pendientes" },
  { id: "procesados", label: "Procesados", href: "/banco/procesados" },
] as const;

/** Barra de pestañas de la Conciliación Bancaria. */
export default function BancoNav() {
  const pathname = usePathname();
  const router = useRouter();
  const actual = SECCIONES.find((s) => pathname.startsWith(s.href))?.id ?? "importar";

  return (
    <Tabs
      value={actual}
      onChange={(_, v) => {
        const seccion = SECCIONES.find((s) => s.id === v);
        if (seccion) router.push(seccion.href);
      }}
      sx={{ mb: 2 }}
      variant="scrollable"
      scrollButtons="auto"
    >
      {SECCIONES.map((s) => (
        <Tab key={s.id} value={s.id} label={s.label} />
      ))}
    </Tabs>
  );
}