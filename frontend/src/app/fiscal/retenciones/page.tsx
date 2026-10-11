"use client";

import { Box, Typography } from "@mui/material";

import ResumenRetenciones from "@/components/ResumenRetenciones";

export default function RetencionesPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Retenciones IRPF (111 / 115)
      </Typography>
      <ResumenRetenciones />
    </Box>
  );
}
