"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Paper,
  Skeleton,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";

import { ApiError, api, type LibroIVAResponse } from "@/lib/api";
import { formatearImporte } from "@/lib/formato";
import { useCargar } from "@/lib/useCargar";

function rangoAnioActual(): { desde: string; hasta: string } {
  const anio = new Date().getFullYear();
  return { desde: `${anio}-01-01`, hasta: `${anio}-12-31` };
}

export default function LibroIVA() {
  const inicial = rangoAnioActual();
  const [origen, setOrigen] = useState<"repercutido" | "soportado">("repercutido");
  const [desde, setDesde] = useState(inicial.desde);
  const [hasta, setHasta] = useState(inicial.hasta);
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, loading, error: errorCarga } = useCargar<LibroIVAResponse>(
    () => api.facturas.libro({ origen, desde, hasta }),
    [origen, desde, hasta]
  );

  async function exportar() {
    setExportando(true);
    setError(null);
    try {
      await api.facturas.exportarLibro({ origen, desde, hasta });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al exportar el libro");
    } finally {
      setExportando(false);
    }
  }

  return (
    <Box>
      <Tabs
        value={origen}
        onChange={(_, v: "repercutido" | "soportado") => setOrigen(v)}
        sx={{ mb: 2 }}
      >
        <Tab value="repercutido" label="Repercutido (ventas)" />
        <Tab value="soportado" label="Soportado (compras)" />
      </Tabs>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }} alignItems="center">
        <TextField
          label="Desde"
          type="date"
          size="small"
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Hasta"
          type="date"
          size="small"
          value={hasta}
          onChange={(e) => setHasta(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <Button variant="outlined" disabled={exportando} onClick={exportar}>
          Exportar CSV
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Skeleton variant="rectangular" height={200} />
      ) : errorCarga ? (
        <Typography color="error">{errorCarga}</Typography>
      ) : data ? (
        <>
          <Paper variant="outlined" sx={{ mb: 2 }}>
            <Table size="small" data-testid="tabla-libro-iva">
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Número</TableCell>
                  <TableCell>CIF</TableCell>
                  <TableCell>Tercero</TableCell>
                  <TableCell align="right">Base</TableCell>
                  <TableCell align="right">Tipo</TableCell>
                  <TableCell align="right">Cuota</TableCell>
                  <TableCell align="right">Total</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.operaciones.map((op, i) => (
                  <TableRow key={i} hover>
                    <TableCell>{op.fecha}</TableCell>
                    <TableCell>{op.numero}</TableCell>
                    <TableCell>{op.tercero_cif}</TableCell>
                    <TableCell>{op.tercero_razon_social}</TableCell>
                    <TableCell align="right">{formatearImporte(op.base_imponible)}</TableCell>
                    <TableCell align="right">{formatearImporte(op.tipo_iva)}</TableCell>
                    <TableCell align="right">{formatearImporte(op.cuota_iva)}</TableCell>
                    <TableCell align="right">{formatearImporte(op.total)}</TableCell>
                  </TableRow>
                ))}
                {data.operaciones.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      Sin operaciones en el periodo.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Paper>

          <Typography variant="subtitle2" gutterBottom>
            Totales por tipo de IVA
          </Typography>
          <Paper variant="outlined">
            <Table size="small" data-testid="totales-libro-iva">
              <TableHead>
                <TableRow>
                  <TableCell>Tipo</TableCell>
                  <TableCell align="right">Base</TableCell>
                  <TableCell align="right">Cuota</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.totales_por_tipo.map((t) => (
                  <TableRow key={t.tipo_iva}>
                    <TableCell>{formatearImporte(t.tipo_iva)} %</TableCell>
                    <TableCell align="right">{formatearImporte(t.base)}</TableCell>
                    <TableCell align="right">{formatearImporte(t.cuota)}</TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Total</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    {formatearImporte(data.total_base)}
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    {formatearImporte(data.total_cuota)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Paper>
        </>
      ) : null}
    </Box>
  );
}
