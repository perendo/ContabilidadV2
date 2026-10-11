"use client";

import { Box, Typography } from "@mui/material";

import BancoNav from "@/components/BancoNav";
import BancoReglas from "@/components/BancoReglas";

export default function BancoReglasPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Conciliación bancaria
      </Typography>
      <BancoNav />
      <BancoReglas />
    </Box>
  );
}