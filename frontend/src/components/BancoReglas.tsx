"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  NativeSelect,
  Paper,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { ApiError, api, type MatchItem, type ReglaBanco, type ReglaBancoIn } from "@/lib/api";
import { formatearImporte } from "@/lib/formato";
import { useCargar } from "@/lib/useCargar";

interface FormRegla {
  nombre: string;
  patron_regex: string;
  cuenta_debe: string;
  cuenta_haber: string;
  importe_fijo: string;
  porcentaje: string;
  prioridad: number;
  auto_asentar: boolean;
  activa: boolean;
}

function reglaVacia(): FormRegla {
  return {
    nombre: "",
    patron_regex: "",
    cuenta_debe: "",
    cuenta_haber: "",
    importe_fijo: "",
    porcentaje: "",
    prioridad: 0,
    auto_asentar: false,
    activa: true,
  };
}

export default function BancoReglas() {
  const reglasQ = useCargar(() => api.banco.reglas(), []);
  const cuentasQ = useCargar(() => api.todasLasCuentas(), []);

  const [modalAbierto, setModalAbierto] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [form, setForm] = useState<FormRegla>(reglaVacia());
  const [guardando, setGuardando] = useState(false);
  const [simulando, setSimulando] = useState<ReglaBanco | null>(null);
  const [matches, setMatches] = useState<MatchItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cuentas = cuentasQ.data ?? [];
  const cuentaNombre = (codigo: string) =>
    cuentas.find((c) => c.codigo === codigo)?.nombre ?? codigo;

  function abrirNueva() {
    setEditandoId(null);
    setForm(reglaVacia());
    setError(null);
    setModalAbierto(true);
  }

  function abrirEdicion(regla: ReglaBanco) {
    setEditandoId(regla.id);
    setForm({
      nombre: regla.nombre,
      patron_regex: regla.patron_regex,
      cuenta_debe: regla.cuenta_debe,
      cuenta_haber: regla.cuenta_haber,
      importe_fijo: regla.importe_fijo ?? "",
      porcentaje: regla.porcentaje ?? "",
      prioridad: regla.prioridad,
      auto_asentar: regla.auto_asentar,
      activa: regla.activa,
    });
    setError(null);
    setModalAbierto(true);
  }

  function actualizar<K extends keyof FormRegla>(campo: K, valor: FormRegla[K]) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  async function guardar() {
    setError(null);
    if (!form.nombre.trim() || !form.patron_regex.trim() || !form.cuenta_debe || !form.cuenta_haber) {
      setError("Completa nombre, patrón y ambas cuentas.");
      return;
    }
    try {
      new RegExp(form.patron_regex);
    } catch {
      setError("El patrón regex no es válido.");
      return;
    }
    const payload: ReglaBancoIn = {
      nombre: form.nombre.trim(),
      patron_regex: form.patron_regex.trim(),
      cuenta_debe: form.cuenta_debe,
      cuenta_haber: form.cuenta_haber,
      importe_fijo: form.importe_fijo.trim() ? form.importe_fijo.trim() : null,
      porcentaje: form.porcentaje.trim() ? form.porcentaje.trim() : null,
      prioridad: form.prioridad,
      auto_asentar: form.auto_asentar,
      activa: form.activa,
    };
    setGuardando(true);
    try {
      if (editandoId !== null) {
        await api.banco.actualizarRegla(editandoId, payload);
      } else {
        await api.banco.crearRegla(payload);
      }
      setModalAbierto(false);
      reglasQ.recargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al guardar la regla");
    } finally {
      setGuardando(false);
    }
  }

  async function simular(regla: ReglaBanco) {
    setSimulando(regla);
    setMatches(null);
    setError(null);
    try {
      const res = await api.banco.simularRegla(regla.id);
      setMatches(res.matches);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al simular la regla");
      setSimulando(null);
    }
  }

  async function eliminar(regla: ReglaBanco) {
    if (!window.confirm(`¿Eliminar la regla "${regla.nombre}"?`)) return;
    try {
      await api.banco.borrarRegla(regla.id);
      reglasQ.recargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al eliminar la regla");
    }
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
        <Button variant="contained" onClick={abrirNueva}>
          Crear regla
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small" aria-label="Reglas de auto-matching">
          <TableHead>
            <TableRow>
              <TableCell>Nombre</TableCell>
              <TableCell>Patrón</TableCell>
              <TableCell>Cuenta Debe</TableCell>
              <TableCell>Cuenta Haber</TableCell>
              <TableCell align="right">Prioridad</TableCell>
              <TableCell align="center">Auto asentar</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(reglasQ.data ?? []).length === 0 && !reglasQ.loading && (
              <TableRow>
                <TableCell colSpan={7}>Sin reglas configuradas.</TableCell>
              </TableRow>
            )}
            {(reglasQ.data ?? []).map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.nombre}</TableCell>
                <TableCell>
                  <code>{r.patron_regex}</code>
                </TableCell>
                <TableCell>
                  {r.cuenta_debe} · {cuentaNombre(r.cuenta_debe)}
                </TableCell>
                <TableCell>
                  {r.cuenta_haber} · {cuentaNombre(r.cuenta_haber)}
                </TableCell>
                <TableCell align="right">{r.prioridad}</TableCell>
                <TableCell align="center">
                  {r.auto_asentar ? <Chip size="small" color="success" label="Sí" /> : <Chip size="small" label="No" />}
                </TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => simular(r)}>
                    Simular
                  </Button>
                  <Button size="small" onClick={() => abrirEdicion(r)}>
                    Editar
                  </Button>
                  <Button size="small" color="error" onClick={() => eliminar(r)}>
                    Eliminar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Modal crear / editar regla */}
      <Dialog open={modalAbierto} onClose={() => setModalAbierto(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editandoId !== null ? "Editar regla" : "Nueva regla"}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
            <TextField
              label="Nombre"
              value={form.nombre}
              onChange={(e) => actualizar("nombre", e.target.value)}
              fullWidth
              margin="dense"
            />
            <TextField
              label="Patrón regex"
              value={form.patron_regex}
              onChange={(e) => actualizar("patron_regex", e.target.value)}
              fullWidth
              margin="dense"
              helperText="Se aplica a concepto y referencia del movimiento"
            />
            <FormControl fullWidth margin="dense">
              <InputLabel htmlFor="regla-cuenta-debe">Cuenta debe</InputLabel>
              <NativeSelect
                id="regla-cuenta-debe"
                value={form.cuenta_debe}
                onChange={(e) => actualizar("cuenta_debe", e.target.value)}
              >
                <option value="">Selecciona…</option>
                {cuentas.map((c) => (
                  <option key={c.id} value={c.codigo}>
                    {c.codigo} - {c.nombre}
                  </option>
                ))}
              </NativeSelect>
            </FormControl>
            <FormControl fullWidth margin="dense">
              <InputLabel htmlFor="regla-cuenta-haber">Cuenta haber</InputLabel>
              <NativeSelect
                id="regla-cuenta-haber"
                value={form.cuenta_haber}
                onChange={(e) => actualizar("cuenta_haber", e.target.value)}
              >
                <option value="">Selecciona…</option>
                {cuentas.map((c) => (
                  <option key={c.id} value={c.codigo}>
                    {c.codigo} - {c.nombre}
                  </option>
                ))}
              </NativeSelect>
            </FormControl>
            <Box sx={{ display: "flex", gap: 2 }}>
              <TextField
                label="Importe fijo"
                value={form.importe_fijo}
                onChange={(e) => actualizar("importe_fijo", e.target.value)}
                fullWidth
                margin="dense"
              />
              <TextField
                label="Porcentaje (%)"
                value={form.porcentaje}
                onChange={(e) => actualizar("porcentaje", e.target.value)}
                fullWidth
                margin="dense"
              />
            </Box>
            <TextField
              label="Prioridad"
              type="number"
              inputProps={{ min: 0 }}
              value={String(form.prioridad)}
              onChange={(e) => actualizar("prioridad", Number(e.target.value) || 0)}
              fullWidth
              margin="dense"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.auto_asentar}
                  onChange={(e) => actualizar("auto_asentar", e.target.checked)}
                />
              }
              label="Auto asentar"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.activa}
                  onChange={(e) => actualizar("activa", e.target.checked)}
                />
              }
              label="Activa"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalAbierto(false)}>Cancelar</Button>
          <Button variant="contained" onClick={guardar} disabled={guardando}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal simular */}
      <Dialog open={!!simulando} onClose={() => setSimulando(null)} maxWidth="md" fullWidth>
        <DialogTitle>Simulación de &quot;{simulando?.nombre}&quot;</DialogTitle>
        <DialogContent>
          {matches === null ? (
            <Typography variant="body2">Cargando movimientos…</Typography>
          ) : matches.length === 0 ? (
            <Typography variant="body2">Ningún movimiento pendiente coincide con la regla.</Typography>
          ) : (
            <TableContainer>
              <Table size="small" aria-label="Matches de la simulación">
                <TableHead>
                  <TableRow>
                    <TableCell>Fecha operación</TableCell>
                    <TableCell>Concepto</TableCell>
                    <TableCell align="right">Importe</TableCell>
                    <TableCell>Cuenta D</TableCell>
                    <TableCell>Cuenta H</TableCell>
                    <TableCell align="right">Importe calculado</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {matches.map((m) => (
                    <TableRow key={m.movimiento_id}>
                      <TableCell>{m.fecha_operacion}</TableCell>
                      <TableCell>{m.concepto}</TableCell>
                      <TableCell align="right">{formatearImporte(m.importe)}</TableCell>
                      <TableCell>{m.cuenta_debe}</TableCell>
                      <TableCell>{m.cuenta_haber}</TableCell>
                      <TableCell align="right">{formatearImporte(m.importe_calculado)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSimulando(null)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}