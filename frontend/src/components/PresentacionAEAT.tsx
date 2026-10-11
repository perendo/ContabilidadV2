"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import { ApiError, api, type PresentacionVista } from "@/lib/api";
import { formatearImporte } from "@/lib/formato";
import { useCargar } from "@/lib/useCargar";

const MODELOS = ["303", "111", "115", "200"] as const;
type Modelo = (typeof MODELOS)[number];

function periodoPorDefecto(modelo: Modelo): string {
  const anio = new Date().getFullYear();
  return modelo === "200" ? String(anio) : `${anio}T1`;
}

const ETIQUETAS_RESUMEN: Record<string, string> = {
  base_repercutida: "Base repercutida",
  cuota_repercutida: "Cuota repercutida",
  base_soportada: "Base soportada",
  cuota_soportada: "Cuota soportada",
  resultante: "Resultado de la liquidación",
  base_retenciones: "Base de retenciones",
  cuota_retenciones: "Retenciones practicadas",
  numero_perceptores: "Nº perceptores",
  resultado_contable: "Resultado contable",
  aumentos: "Aumentos",
  disminuciones: "Disminuciones",
  base_imponible: "Base imponible",
  cuota_integra: "Cuota íntegra",
  retenciones_pagos_cuenta: "Retenciones y pagos a cuenta",
  cuota_diferencial: "Cuota diferencial",
};

function esMonetario(clave: string): boolean {
  return clave !== "numero_perceptores";
}

export default function PresentacionAEAT() {
  const [modelo, setModelo] = useState<Modelo>("303");
  const [periodo, setPeriodo] = useState(() => periodoPorDefecto("303"));
  const [descargando, setDescargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, loading, error: errorCarga } = useCargar<PresentacionVista>(
    () => api.presentaciones.vista(modelo, periodo),
    [modelo, periodo]
  );

  function cambiarModelo(m: Modelo) {
    setModelo(m);
    setPeriodo(periodoPorDefecto(m));
    setError(null);
  }

  async function descargar() {
    setDescargando(true);
    setError(null);
    try {
      await api.presentaciones.descargarFichero(modelo, periodo);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al descargar el fichero");
    } finally {
      setDescargando(false);
    }
  }

  const habilitado = data?.bloque_descarga.habilitado ?? false;

  return (
    <Box data-testid="presentacion-aeat">
      <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap">
        <TextField
          select
          label="Modelo"
          size="small"
          value={modelo}
          onChange={(e) => cambiarModelo(e.target.value as Modelo)}
          sx={{ width: 140 }}
        >
          {MODELOS.map((m) => (
            <MenuItem key={m} value={m}>
              Modelo {m}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Periodo"
          size="small"
          value={periodo}
          onChange={(e) => setPeriodo(e.target.value)}
          helperText={modelo === "200" ? "Ej.: 2026" : "Ej.: 2026T1"}
          inputProps={{ "data-testid": "periodo" }}
        />
        <Tooltip title={habilitado ? "" : data?.bloque_descarga.motivo ?? ""}>
          <span>
            <Button
              variant="contained"
              disabled={descargando || !habilitado || loading}
              onClick={descargar}
              data-testid="descargar-fichero"
            >
              Descargar fichero
            </Button>
          </span>
        </Tooltip>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Skeleton variant="rectangular" height={200} />
      ) : errorCarga ? (
        <Alert severity="warning">{errorCarga}</Alert>
      ) : data ? (
        <>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
            <Chip
              label={data.cerrada ? "Liquidación/periodo cerrado" : "Borrador"}
              color={data.cerrada ? "success" : "default"}
              size="small"
            />
            {!habilitado && data.bloque_descarga.motivo && (
              <Typography variant="body2" color="text.secondary">
                {data.bloque_descarga.motivo}
              </Typography>
            )}
          </Stack>

          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Resumen
            </Typography>
            <Table size="small" data-testid="resumen-presentacion">
              <TableBody>
                {Object.entries(data.resumen).map(([clave, valor]) => (
                  <TableRow key={clave}>
                    <TableCell>{ETIQUETAS_RESUMEN[clave] ?? clave}</TableCell>
                    <TableCell align="right">
                      {valor === null
                        ? "—"
                        : esMonetario(clave)
                          ? formatearImporte(String(valor))
                          : String(valor)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          <Typography variant="subtitle2" gutterBottom>
            Casillas
          </Typography>
          <Paper variant="outlined">
            <Table size="small" data-testid="casillas-presentacion">
              <TableHead>
                <TableRow>
                  <TableCell>Casilla</TableCell>
                  <TableCell>Concepto</TableCell>
                  <TableCell align="right">Importe</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.casillas.map((c) => (
                  <TableRow key={c.casilla}>
                    <TableCell>{c.casilla}</TableCell>
                    <TableCell>{c.label}</TableCell>
                    <TableCell align="right">{formatearImporte(c.importe)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      ) : null}
    </Box>
  );
}
