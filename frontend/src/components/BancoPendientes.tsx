"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
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

import {
  ApiError,
  api,
  onChangeContexto,
  type Cuenta,
  type MovimientoBanco,
  type ProcesarResponse,
} from "@/lib/api";
import ImporteInput from "@/components/ImporteInput";
import { formatearImporte } from "@/lib/formato";

const LIMIT = 50;

export default function BancoPendientes() {
  const [movimientos, setMovimientos] = useState<MovimientoBanco[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [codigo, setCodigo] = useState("");
  const [offset, setOffset] = useState(0);
  const [hayMas, setHayMas] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [resProcesar, setResProcesar] = useState<ProcesarResponse | null>(null);
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);

  // Asiento manual
  const [modalMov, setModalMov] = useState<MovimientoBanco | null>(null);
  const [cuentaDebeId, setCuentaDebeId] = useState("");
  const [debeText, setDebeText] = useState("");
  const [cuentaHaberId, setCuentaHaberId] = useState("");
  const [haberText, setHaberText] = useState("");
  const [asentarAlGuardar, setAsentarAlGuardar] = useState(false);
  const [guardandoAsiento, setGuardandoAsiento] = useState(false);

  const cargar = useCallback(
    async (nuevoOffset: number) => {
      setCargando(true);
      setError(null);
      try {
        const items = await api.banco.pendientes({
          desde: desde || undefined,
          hasta: hasta || undefined,
          codigo_banco: codigo || undefined,
          offset: nuevoOffset,
          limit: LIMIT,
        });
        setMovimientos(items);
        setOffset(nuevoOffset);
        setHayMas(items.length === LIMIT);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Error al cargar los pendientes");
      } finally {
        setCargando(false);
      }
    },
    [desde, hasta, codigo]
  );

  const cargarRef = useRef(cargar);
  cargarRef.current = cargar;

  useEffect(() => {
    cargarRef.current(0);
    const off = onChangeContexto(() => cargarRef.current(0));
    return off;
  }, []);

  useEffect(() => {
    api.todasLasCuentas().then(setCuentas).catch(() => setCuentas([]));
  }, []);

  async function procesarAutomatico() {
    setProcesando(true);
    setError(null);
    setResProcesar(null);
    try {
      setResProcesar(
        await api.banco.procesar({ desde: desde || undefined, hasta: hasta || undefined })
      );
      cargarRef.current(0);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al procesar");
    } finally {
      setProcesando(false);
    }
  }

  function abrirAsiento(mov: MovimientoBanco) {
    const importe = Number(mov.importe);
    const esCargo = importe < 0;
    const importeAbs = Math.abs(importe).toFixed(2);
    setModalMov(mov);
    setCuentaDebeId("");
    setDebeText(esCargo ? importeAbs : "0.00");
    setCuentaHaberId("");
    setHaberText(esCargo ? "0.00" : importeAbs);
    setAsentarAlGuardar(false);
    setError(null);
  }

  async function guardarYProcesar() {
    if (!modalMov) return;
    if (!cuentaDebeId || !cuentaHaberId) {
      setError("Selecciona ambas cuentas del asiento.");
      return;
    }
    setGuardandoAsiento(true);
    setError(null);
    try {
      let asiento = await api.guardarAsiento({
        fecha: modalMov.fecha_valor,
        concepto: modalMov.concepto,
        apuntes: [
          { cuenta_id: Number(cuentaDebeId), debe: debeText || "0.00", haber: "0.00" },
          { cuenta_id: Number(cuentaHaberId), debe: "0.00", haber: haberText || "0.00" },
        ],
      });
      if (asentarAlGuardar) {
        asiento = await api.asentarAsiento(asiento.id);
      }
      await api.banco.marcarProcesado(modalMov.id, asiento.id);
      setModalMov(null);
      cargarRef.current(0);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al crear el asiento");
    } finally {
      setGuardandoAsiento(false);
    }
  }

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, alignItems: "center" }}>
          <TextField
            label="Desde"
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            label="Hasta"
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            label="Código de banco"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />
          <Button variant="outlined" onClick={() => cargarRef.current(0)}>
            Buscar
          </Button>
          <Box sx={{ flexGrow: 1 }} />
          <Button
            variant="contained"
            onClick={procesarAutomatico}
            disabled={procesando || movimientos.length === 0}
          >
            {procesando ? "Procesando…" : "Procesar automático"}
          </Button>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {resProcesar && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setResProcesar(null)}>
          Procesamiento completado: {resProcesar.creados} asientos creados ·{" "}
          {resProcesar.pendientes} pendientes · {resProcesar.fallidos.length} fallidos.
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small" aria-label="Movimientos pendientes de conciliar">
          <TableHead>
            <TableRow>
              <TableCell>Fecha valor</TableCell>
              <TableCell>Concepto</TableCell>
              <TableCell align="right">Importe</TableCell>
              <TableCell align="right">Saldo</TableCell>
              <TableCell>Código</TableCell>
              <TableCell>Referencias</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!cargando && movimientos.length === 0 && (
              <TableRow>
                <TableCell colSpan={7}>No hay movimientos pendientes de conciliar.</TableCell>
              </TableRow>
            )}
            {movimientos.map((m) => (
              <TableRow key={m.id}>
                <TableCell>{m.fecha_valor}</TableCell>
                <TableCell>{m.concepto}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 500 }}>
                  {formatearImporte(m.importe)}
                </TableCell>
                <TableCell align="right">{formatearImporte(m.saldo)}</TableCell>
                <TableCell>{m.codigo_banco ?? "—"}</TableCell>
                <TableCell>
                  {[m.referencia, m.referencia_2].filter(Boolean).join(" · ") || "—"}
                </TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => abrirAsiento(m)}>
                    Crear asiento
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
        {hayMas && (
          <Button onClick={() => cargarRef.current(offset + LIMIT)}>Cargar más</Button>
        )}
      </Box>

      {/* Modal: crear asiento manual desde un movimiento */}
      <Dialog open={!!modalMov} onClose={() => setModalMov(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Crear asiento desde movimiento</DialogTitle>
        <DialogContent>
          {modalMov && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                {modalMov.fecha_valor} · {modalMov.concepto} ·{" "}
                {formatearImporte(modalMov.importe)}
              </Typography>
              <FormControl fullWidth>
                <InputLabel htmlFor="pendiente-cuenta-debe">Cuenta (debe)</InputLabel>
                <NativeSelect
                  id="pendiente-cuenta-debe"
                  value={cuentaDebeId}
                  onChange={(e) => setCuentaDebeId(e.target.value)}
                >
                  <option value="">Selecciona…</option>
                  {cuentas.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.codigo} - {c.nombre}
                    </option>
                  ))}
                </NativeSelect>
              </FormControl>
              <ImporteInput label="Debe" value={debeText} onChange={setDebeText} />
              <FormControl fullWidth>
                <InputLabel htmlFor="pendiente-cuenta-haber">Cuenta (haber)</InputLabel>
                <NativeSelect
                  id="pendiente-cuenta-haber"
                  value={cuentaHaberId}
                  onChange={(e) => setCuentaHaberId(e.target.value)}
                >
                  <option value="">Selecciona…</option>
                  {cuentas.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.codigo} - {c.nombre}
                    </option>
                  ))}
                </NativeSelect>
              </FormControl>
              <ImporteInput label="Haber" value={haberText} onChange={setHaberText} />
              <FormControlLabel
                control={
                  <Switch
                    checked={asentarAlGuardar}
                    onChange={(e) => setAsentarAlGuardar(e.target.checked)}
                  />
                }
                label="Asentar al guardar"
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalMov(null)}>Cancelar</Button>
          <Button variant="contained" onClick={guardarYProcesar} disabled={guardandoAsiento}>
            {guardandoAsiento ? "Guardando…" : "Guardar y procesar"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}