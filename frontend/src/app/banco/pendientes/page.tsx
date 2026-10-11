"use client";

import { Box, Typography } from "@mui/material";

import BancoNav from "@/components/BancoNav";
import BancoPendientes from "@/components/BancoPendientes";

export default function BancoPendientesPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Conciliación bancaria
      </Typography>
      <BancoNav />
      <BancoPendientes />
    </Box>
  );
}