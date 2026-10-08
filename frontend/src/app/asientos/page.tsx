"use client";

import { Suspense, useState } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";
import { useSearchParams } from "next/navigation";

import FormAsiento from "@/components/FormAsiento";
import { api, getEjercicioId } from "@/lib/api";
import { useCargar } from "@/lib/useCargar";

function AsientoNuevo() {
  const params = useSearchParams();
  const borradorId = params.get("borrador");
  const [guardadoId, setGuardadoId] = useState<number | null>(null);

  const cuentasQ = useCargar(() => api.cuentas({ limit: 500 }), []);
  const ejerciciosQ = useCargar(() => api.ejercicios(), []);
  const detalleQ = useCargar(
    () => (borradorId ? api.asientoDetalle(Number(borradorId)) : Promise.resolve(null)),
    [borradorId]
  );

  if (cuentasQ.loading || ejerciciosQ.loading || detalleQ.loading) {
    return <CircularProgress />;
  }
  if (cuentasQ.error || ejerciciosQ.error) {
    return <Typography color="error">{cuentasQ.error ?? ejerciciosQ.error}</Typography>;
  }

  const ejercicioId = getEjercicioId();
  const ejercicio = ejerciciosQ.data?.find((e) => String(e.id) === ejercicioId);
  const ejercicioAbierto = ejercicio?.estado === "abierto";
  const edicion = detalleQ.data;
  const editandoId = edicion?.id ?? guardadoId;

  const guardar = async (payload: {
    fecha: string;
    concepto: string;
    apuntes: { cuenta_id: number; debe: string; haber: string }[];
  }) => {
    if (editandoId) {
      await api.editarAsiento(editandoId, payload);
    } else {
      const creado = await api.guardarAsiento(payload);
      setGuardadoId(creado.id);
    }
  };

  const asentar = async (payload: {
    fecha: string;
    concepto: string;
    apuntes: { cuenta_id: number; debe: string; haber: string }[];
  }) => {
    let id = editandoId;
    if (id) {
      await api.editarAsiento(id, payload);
    } else {
      const creado = await api.guardarAsiento(payload);
      id = creado.id;
      setGuardadoId(id);
    }
    await api.asentarAsiento(id);
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        {editandoId ? `Editar borrador #${editandoId}` : "Nuevo asiento"}
      </Typography>
      <FormAsiento
        key={editandoId ?? "nuevo"}
        cuentas={cuentasQ.data?.items ?? []}
        ejercicioAbierto={!!ejercicioAbierto}
        inicial={edicion ?? null}
        onGuardarBorrador={guardar}
        onAsentar={asentar}
      />
    </Box>
  );
}

export default function AsientosPage() {
  return (
    <Suspense fallback={<CircularProgress />}>
      <AsientoNuevo />
    </Suspense>
  );
}