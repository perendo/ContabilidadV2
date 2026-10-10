"use client";

import { Suspense } from "react";
import Mayor from "@/components/Mayor";

export default function MayorPage() {
  return (
    <Suspense fallback={<div>Cargando Libro Mayor...</div>}>
      <Mayor />
    </Suspense>
  );
}