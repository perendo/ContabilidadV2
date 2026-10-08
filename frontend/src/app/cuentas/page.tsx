"use client";

import { Typography } from "@mui/material";

import PlanCuentas from "@/components/PlanCuentas";

export default function CuentasPage() {
  return (
    <>
      <Typography variant="h5" gutterBottom>
        Plan de cuentas
      </Typography>
      <PlanCuentas />
    </>
  );
}