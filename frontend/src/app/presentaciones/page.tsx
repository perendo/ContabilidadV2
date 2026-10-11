"use client";

import { Box, Typography } from "@mui/material";

import PresentacionAEAT from "@/components/PresentacionAEAT";

export default function PresentacionesPage() {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Presentación AEAT
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Vista de los modelos 303, 111, 115 y 200 y descarga del fichero de posiciones fijas (solo con
        la liquidación o el periodo cerrados).
      </Typography>
      <PresentacionAEAT />
    </Box>
  );
}
