"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Skeleton,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { ApiError, api } from "@/lib/api";
import { useCargar } from "@/lib/useCargar";

export default function PlanCuentas() {
  const [busqueda, setBusqueda] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [nueva, setNueva] = useState({ codigo: "", nombre: "", nivel: 4 });
  const [error, setError] = useState<string | null>(null);

  const { data, loading, recargar } = useCargar(
    () => api.cuentas({ query: busqueda || undefined }),
    [busqueda]
  );

  async function crear() {
    try {
      await api.crearCuenta(nueva);
      setAbierto(false);
      setNueva({ codigo: "", nombre: "", nivel: 4 });
      recargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al crear la cuenta");
    }
  }

  return (
    <Box>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField
          label="Buscar cuenta"
          size="small"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          sx={{ flexGrow: 1 }}
        />
        <Button variant="contained" onClick={() => setAbierto(true)}>
          Nueva cuenta
        </Button>
      </Stack>

      {loading ? (
        <Skeleton variant="rectangular" height={200} />
      ) : data && data.items.length > 0 ? (
        <Table data-testid="tabla-cuentas">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell align="right">Nivel</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.items.map((c) => (
              <TableRow key={c.id}>
                <TableCell>{c.codigo}</TableCell>
                <TableCell>{c.nombre}</TableCell>
                <TableCell align="right">{c.nivel}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <Typography color="text.secondary" data-testid="empty-cuentas">
          No hay cuentas en este ejercicio.
        </Typography>
      )}

      <Dialog open={abierto} onClose={() => setAbierto(false)}>
        <DialogTitle>Nueva cuenta</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
          <TextField
            label="Código (solo dígitos)"
            value={nueva.codigo}
            onChange={(e) => setNueva({ ...nueva, codigo: e.target.value })}
          />
          <TextField
            label="Nombre"
            value={nueva.nombre}
            onChange={(e) => setNueva({ ...nueva, nombre: e.target.value })}
          />
          <TextField
            label="Nivel (1-5)"
            type="number"
            value={nueva.nivel}
            onChange={(e) => setNueva({ ...nueva, nivel: Number(e.target.value) })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAbierto(false)}>Cancelar</Button>
          <Button variant="contained" onClick={crear}>
            Crear
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!error} autoHideDuration={5000} onClose={() => setError(null)}>
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
}