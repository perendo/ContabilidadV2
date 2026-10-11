"use client";

import { Box, Typography } from "@mui/material";

import LibroIVA from "@/components/LibroIVA";

export default function LibrosIVAPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Libros Registro de IVA
      </Typography>
      <LibroIVA />
    </Box>
  );
}
