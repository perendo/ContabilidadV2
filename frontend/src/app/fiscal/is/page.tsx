"use client";

import { Box, Typography } from "@mui/material";

import LiquidacionIS from "@/components/LiquidacionIS";

export default function ImpuestoSociedadesPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Liquidación del Impuesto sobre Sociedades
      </Typography>
      <LiquidacionIS />
    </Box>
  );
}
