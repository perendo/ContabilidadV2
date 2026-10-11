"use client";

import { Box, Button, Skeleton, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import Link from "next/link";

import { api } from "@/lib/api";
import { useCargar } from "@/lib/useCargar";

export default function FacturasPage() {
  const { data, loading, error } = useCargar(() => api.facturas.listar({ limit: 100 }), []);

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">Facturas</Typography>
        <Button variant="contained" component={Link} href="/facturas/nueva">
          Nueva factura
        </Button>
      </Stack>

      {loading ? (
        <Skeleton variant="rectangular" height={200} />
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : data && data.items.length > 0 ? (
        <Table data-testid="tabla-facturas">
          <TableHead>
            <TableRow>
              <TableCell>Fecha</TableCell>
              <TableCell>Número</TableCell>
              <TableCell>Origen</TableCell>
              <TableCell>CIF</TableCell>
              <TableCell>Tercero</TableCell>
              <TableCell>Retención</TableCell>
              <TableCell align="right">Asiento</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.items.map((f) => (
              <TableRow key={f.id} hover>
                <TableCell>{f.fecha}</TableCell>
                <TableCell>{f.numero}</TableCell>
                <TableCell>{f.origen}</TableCell>
                <TableCell>{f.tercero_cif}</TableCell>
                <TableCell>{f.tercero_razon_social}</TableCell>
                <TableCell>{f.tipo_retencion ?? "—"}</TableCell>
                <TableCell align="right">{f.asiento_id ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <Typography color="text.secondary">No hay facturas registradas en este ejercicio.</Typography>
      )}
    </Box>
  );
}
