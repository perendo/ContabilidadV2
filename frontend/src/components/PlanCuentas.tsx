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
  IconButton,
  Skeleton,
  Snackbar,
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
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";

import { ApiError, api, type Cuenta } from "@/lib/api";
import { useCargar } from "@/lib/useCargar";

export default function PlanCuentas() {
  const [busqueda, setBusqueda] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [padre, setPadre] = useState<Cuenta | null>(null);
  const [nueva, setNueva] = useState({ codigo: "", nombre: "", nivel: 4 });
  const [error, setError] = useState<string | null>(null);

  const { data, loading, recargar } = useCargar(
    () => api.cuentas({ query: busqueda || undefined }),
    [busqueda]
  );

  function abrirCuenta() {
    setPadre(null);
    setNueva({ codigo: "", nombre: "", nivel: 4 });
    setAbierto(true);
  }

  function abrirSubcuenta(cuenta: Cuenta) {
    setPadre(cuenta);
    setNueva({ codigo: cuenta.codigo, nombre: "", nivel: Math.min(cuenta.nivel + 1, 5) });
    setAbierto(true);
  }

  async function crear() {
    try {
      await api.crearCuenta(nueva);
      setAbierto(false);
      setPadre(null);
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
        <Button variant="contained" onClick={abrirCuenta}>
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
              <TableCell align="right">Subcuenta</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.items.map((c) => (
              <TableRow key={c.id} hover>
                <TableCell
                  sx={{
                    pl: 2 + (c.nivel - 1) * 2.5,
                    fontFamily: "monospace",
                    fontWeight: c.nivel <= 2 ? 700 : 400,
                  }}
                >
                  {c.codigo}
                </TableCell>
                <TableCell sx={{ fontWeight: c.nivel <= 2 ? 600 : 400 }}>{c.nombre}</TableCell>
                <TableCell align="right">{c.nivel}</TableCell>
                <TableCell align="right">
                  {c.nivel < 5 && (
                    <Tooltip title={`Añadir subcuenta de ${c.codigo}`}>
                      <IconButton
                        size="small"
                        onClick={() => abrirSubcuenta(c)}
                        aria-label={`subcuenta-${c.codigo}`}
                      >
                        <AddCircleOutlineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </TableCell>
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
        <DialogTitle>{padre ? "Nueva subcuenta" : "Nueva cuenta"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
          {padre && (
            <Alert severity="info" icon={false}>
              Subcuenta de <strong>{padre.codigo}</strong> · {padre.nombre}
            </Alert>
          )}
          <TextField
            label="Código (solo dígitos)"
            value={nueva.codigo}
            onChange={(e) => setNueva({ ...nueva, codigo: e.target.value })}
            helperText={padre ? "Se propone el código de la cuenta padre; añade el dígito/s de la subcuenta" : undefined}
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
