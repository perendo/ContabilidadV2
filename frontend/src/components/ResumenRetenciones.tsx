"use client";

import { useState } from "react";
import {
  Box,
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

import { api, type RetencionesResponse } from "@/lib/api";
import { formatearImporte } from "@/lib/formato";
import { useCargar } from "@/lib/useCargar";

function rangoAnioActual(): { desde: string; hasta: string } {
  const anio = new Date().getFullYear();
  return { desde: `${anio}-01-01`, hasta: `${anio}-12-31` };
}

export default function ResumenRetenciones() {
  const inicial = rangoAnioActual();
  const [tipo, setTipo] = useState<"111" | "115">("111");
  const [desde, setDesde] = useState(inicial.desde);
  const [hasta, setHasta] = useState(inicial.hasta);

  const { data, loading, error } = useCargar<RetencionesResponse>(
    () => api.facturas.retenciones({ tipo, desde, hasta }),
    [tipo, desde, hasta]
  );

  return (
    <Box>
      <Tabs value={tipo} onChange={(_, v: "111" | "115") => setTipo(v)} sx={{ mb: 2 }}>
        <Tab value="111" label="111 · Profesionales" />
        <Tab value="115" label="115 · Alquileres" />
      </Tabs>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
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
      </Stack>

      {loading ? (
        <Skeleton variant="rectangular" height={200} />
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : data ? (
        <Table size="small" data-testid="tabla-retenciones">
          <TableHead>
            <TableRow>
              <TableCell>CIF</TableCell>
              <TableCell>Perceptor</TableCell>
              <TableCell align="right">Facturas</TableCell>
              <TableCell align="right">Base</TableCell>
              <TableCell align="right">Retención</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.por_perceptor.map((p) => (
              <TableRow key={p.tercero_cif} hover>
                <TableCell>{p.tercero_cif}</TableCell>
                <TableCell>{p.tercero_razon_social}</TableCell>
                <TableCell align="right">{p.numero_facturas}</TableCell>
                <TableCell align="right">{formatearImporte(p.base_retencion)}</TableCell>
                <TableCell align="right">{formatearImporte(p.cuota_retencion)}</TableCell>
              </TableRow>
            ))}
            {data.por_perceptor.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  Sin retenciones en el periodo.
                </TableCell>
              </TableRow>
            )}
            <TableRow>
              <TableCell colSpan={3} sx={{ fontWeight: 700 }}>
                Total
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {formatearImporte(data.total_base)}
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>
                {formatearImporte(data.total_retencion)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      ) : null}
    </Box>
  );
}
