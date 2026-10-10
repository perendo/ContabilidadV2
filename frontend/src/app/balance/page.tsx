"use client";

import { Suspense } from "react";
import Balance from "@/components/Balance";

export default function BalancePage() {
  return (
    <Suspense fallback={<div>Cargando Balance...</div>}>
      <Balance />
    </Suspense>
  );
}