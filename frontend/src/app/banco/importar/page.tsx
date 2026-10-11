"use client";

import { Box, Typography } from "@mui/material";

import BancoImportar from "@/components/BancoImportar";
import BancoNav from "@/components/BancoNav";

export default function BancoImportarPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Conciliación bancaria
      </Typography>
      <BancoNav />
      <BancoImportar />
    </Box>
  );
}