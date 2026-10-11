"use client";

import { Box, CircularProgress, Typography } from "@mui/material";

import FormFactura from "@/components/FormFactura";
import { api, getEjercicioId, type FacturaIn } from "@/lib/api";
import { useCargar } from "@/lib/useCargar";

export default function NuevaFacturaPage() {
  const ejerciciosQ = useCargar(() => api.ejercicios(), []);

  if (ejerciciosQ.loading) return <CircularProgress />;
  if (ejerciciosQ.error) return <Typography color="error">{ejerciciosQ.error}</Typography>;

  const ejercicioId = getEjercicioId();
  const ejercicio = ejerciciosQ.data?.find((e) => String(e.id) === ejercicioId);

  const guardar = async (payload: FacturaIn) => {
    await api.facturas.crear(payload);
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Nueva factura
      </Typography>
      <FormFactura ejercicioAbierto={ejercicio?.estado === "abierto"} onGuardar={guardar} />
    </Box>
  );
}
