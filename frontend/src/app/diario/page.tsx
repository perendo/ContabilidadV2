"use client";

import { Typography } from "@mui/material";

import Diario from "@/components/Diario";

export default function DiarioPage() {
  return (
    <>
      <Typography variant="h5" gutterBottom>
        Libro diario
      </Typography>
      <Diario />
    </>
  );
}