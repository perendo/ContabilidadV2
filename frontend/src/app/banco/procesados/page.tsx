"use client";

import { Box, Typography } from "@mui/material";

import BancoNav from "@/components/BancoNav";
import BancoProcesados from "@/components/BancoProcesados";

export default function BancoProcesadosPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Conciliación bancaria
      </Typography>
      <BancoNav />
      <BancoProcesados />
    </Box>
  );
}