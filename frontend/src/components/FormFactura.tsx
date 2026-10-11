"use client";

import { useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { formatearImporte } from "@/lib/formato";
import type { FacturaIn, LineaFacturaIVAIn } from "@/lib/api";

export interface FilaFacturaLinea {
  id: number;
  descripcion: string;
  base: string;
  tipoIva: string;
  exenta: boolean;
  tipoRe: string;
  baseRetencion: string;
  pctRetencion: string;
}

interface Props {
  ejercicioAbierto: boolean;
  onGuardar: (payload: FacturaIn) => Promise<void>;
}

function nuevaFila(id: number): FilaFacturaLinea {
  return {
    id,
    descripcion: "",
    base: "",
    tipoIva: "21",
    exenta: false,
    tipoRe: "",
    baseRetencion: "",
    pctRetencion: "",
  };
}

/** Redondea base × tipo / 100 a céntimos (solo UX: el cálculo definitivo es backend). */
export function cuotaPreview(base: string, tipo: string): string {
  const b = parseFloat((base || "0").replace(",", ".")) || 0;
  const t = parseFloat((tipo || "0").replace(",", ".")) || 0;
  return ((Math.round(b * 100) * Math.round(t * 100)) / 10000 / 100).toFixed(2);
}

export default function FormFactura({ ejercicioAbierto, onGuardar }: Props) {
  const [origen, setOrigen] = useState<"venta" | "compra">("venta");
  const [numero, setNumero] = useState("");
  const [fecha, setFecha] = useState(() => new Date().toISOString().slice(0, 10));
  const [cif, setCif] = useState("");
  const [razon, setRazon] = useState("");
  const [tipoRetencion, setTipoRetencion] = useState<"" | "111" | "115">("");
  const [filas, setFilas] = useState<FilaFacturaLinea[]>(() => [nuevaFila(1)]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const nextIdRef = useRef(1);
  const esCompra = origen === "compra";

  const totalFactura = useMemo(
    () =>
      filas.reduce((acc, f) => {
        const base = parseFloat((f.base || "0").replace(",", ".")) || 0;
        const iva = f.exenta ? 0 : parseFloat(cuotaPreview(f.base, f.tipoIva));
        const re = esCompra && f.tipoRe ? parseFloat(cuotaPreview(f.base, f.tipoRe)) : 0;
        const ret =
          esCompra && tipoRetencion && f.baseRetencion && f.pctRetencion
            ? parseFloat(cuotaPreview(f.baseRetencion, f.pctRetencion))
            : 0;
        return acc + base + iva + re - ret;
      }, 0)
      .toFixed(2),
    [filas, esCompra, tipoRetencion]
  );

  function actualizar<K extends keyof FilaFacturaLinea>(id: number, campo: K, valor: FilaFacturaLinea[K]) {
    setFilas((prev) => prev.map((f) => (f.id === id ? { ...f, [campo]: valor } : f)));
  }

  function anadirFila() {
    setFilas((prev) => [...prev, nuevaFila(++nextIdRef.current)]);
  }

  function quitarFila(id: number) {
    if (filas.length > 1) {
      setFilas((prev) => prev.filter((f) => f.id !== id));
    }
  }

  const valido = useMemo(() => {
    if (numero.trim() === "" || razon.trim() === "") return false;
    if (cif.trim().length !== 9) return false;
    return filas.every((f) => f.descripcion.trim() !== "" && (f.base || "") !== "");
  }, [numero, razon, cif, filas]);

  function construirPayload(): FacturaIn {
    return {
      origen,
      numero,
      fecha,
      tercero_cif: cif,
      tercero_razon_social: razon,
      tipo_retencion: esCompra ? tipoRetencion || null : null,
      lineas: filas.map((f, i): LineaFacturaIVAIn => {
        const linea: LineaFacturaIVAIn = {
          numero_linea: i + 1,
          descripcion: f.descripcion,
          base_imponible: f.base || "0",
          tipo_iva: f.exenta ? "0" : f.tipoIva || "0",
          operacion_exenta: f.exenta,
        };
        if (esCompra && f.tipoRe) linea.tipo_re = f.tipoRe;
        if (esCompra && tipoRetencion && f.baseRetencion && f.pctRetencion) {
          linea.base_retencion = f.baseRetencion;
          linea.pct_retencion = f.pctRetencion;
        }
        return linea;
      }),
    };
  }

  async function guardar() {
    setGuardando(true);
    setError(null);
    setMsg(null);
    try {
      await onGuardar(construirPayload());
      setMsg("Factura registrada y asiento generado");
      setNumero("");
      setFilas([nuevaFila(++nextIdRef.current)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al registrar la factura");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div data-testid="form-factura">
      {!ejercicioAbierto && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          El ejercicio está cerrado: no se pueden registrar facturas.
        </Alert>
      )}
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, mb: 2 }}>
        <FormControl sx={{ minWidth: 140 }}>
          <InputLabel id="origen-label">Origen</InputLabel>
          <Select
            labelId="origen-label"
            label="Origen"
            value={origen}
            onChange={(e) => setOrigen(e.target.value as "venta" | "compra")}
          >
            <MenuItem value="venta">Venta</MenuItem>
            <MenuItem value="compra">Compra</MenuItem>
          </Select>
        </FormControl>
        <TextField
          label="Número"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          inputProps={{ "data-testid": "numero" }}
        />
        <TextField
          label="Fecha"
          type="date"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="CIF/NIF tercero"
          value={cif}
          onChange={(e) => setCif(e.target.value)}
          error={cif !== "" && cif.trim().length !== 9}
          helperText={cif !== "" && cif.trim().length !== 9 ? "9 caracteres" : undefined}
          inputProps={{ "data-testid": "cif", maxLength: 9 }}
        />
        <TextField
          label="Razón social"
          value={razon}
          onChange={(e) => setRazon(e.target.value)}
        />
        {esCompra && (
          <FormControl sx={{ minWidth: 160 }}>
            <InputLabel id="ret-label">Retención</InputLabel>
            <Select
              labelId="ret-label"
              label="Retención"
              value={tipoRetencion}
              onChange={(e) => setTipoRetencion(e.target.value as "" | "111" | "115")}
            >
              <MenuItem value="">Sin retención</MenuItem>
              <MenuItem value="111">111 · Profesionales</MenuItem>
              <MenuItem value="115">115 · Alquileres</MenuItem>
            </Select>
          </FormControl>
        )}
      </Box>

      <Paper variant="outlined" sx={{ p: 1, mb: 2 }}>
        <Table size="small" data-testid="tabla-lineas">
          <TableHead>
            <TableRow>
              <TableCell>Descripción</TableCell>
              <TableCell align="right">Base</TableCell>
              <TableCell align="right">Tipo IVA</TableCell>
              <TableCell align="right">Cuota IVA</TableCell>
              {esCompra && <TableCell align="right">Tipo RE</TableCell>}
              {esCompra && tipoRetencion && <TableCell align="right">Base ret.</TableCell>}
              {esCompra && tipoRetencion && <TableCell align="right">% ret.</TableCell>}
              <TableCell align="center">Exenta</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {filas.map((f) => (
              <TableRow key={f.id}>
                <TableCell>
                  <TextField
                    size="small"
                    value={f.descripcion}
                    onChange={(e) => actualizar(f.id, "descripcion", e.target.value)}
                    inputProps={{ "aria-label": `descripcion-${f.id}` }}
                  />
                </TableCell>
                <TableCell>
                  <TextField
                    size="small"
                    value={f.base}
                    onChange={(e) => actualizar(f.id, "base", e.target.value)}
                    inputProps={{ "aria-label": `base-${f.id}`, inputMode: "decimal" }}
                  />
                </TableCell>
                <TableCell align="right">
                  <TextField
                    size="small"
                    value={f.tipoIva}
                    disabled={f.exenta}
                    onChange={(e) => actualizar(f.id, "tipoIva", e.target.value)}
                    inputProps={{ "aria-label": `tipo-iva-${f.id}`, inputMode: "decimal" }}
                  />
                </TableCell>
                <TableCell align="right">{f.exenta ? "—" : cuotaPreview(f.base, f.tipoIva)}</TableCell>
                {esCompra && (
                  <TableCell align="right">
                    <TextField
                      size="small"
                      value={f.tipoRe}
                      onChange={(e) => actualizar(f.id, "tipoRe", e.target.value)}
                      inputProps={{ "aria-label": `tipo-re-${f.id}`, inputMode: "decimal" }}
                    />
                  </TableCell>
                )}
                {esCompra && tipoRetencion && (
                  <TableCell align="right">
                    <TextField
                      size="small"
                      value={f.baseRetencion}
                      onChange={(e) => actualizar(f.id, "baseRetencion", e.target.value)}
                      inputProps={{ "aria-label": `base-ret-${f.id}`, inputMode: "decimal" }}
                    />
                  </TableCell>
                )}
                {esCompra && tipoRetencion && (
                  <TableCell align="right">
                    <TextField
                      size="small"
                      value={f.pctRetencion}
                      onChange={(e) => actualizar(f.id, "pctRetencion", e.target.value)}
                      inputProps={{ "aria-label": `pct-ret-${f.id}`, inputMode: "decimal" }}
                    />
                  </TableCell>
                )}
                <TableCell align="center">
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={f.exenta}
                        onChange={(e) => actualizar(f.id, "exenta", e.target.checked)}
                      />
                    }
                    label=""
                  />
                </TableCell>
                <TableCell>
                  <Button size="small" disabled={filas.length <= 1} onClick={() => quitarFila(f.id)}>
                    Quitar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 1 }}>
          <Button size="small" onClick={anadirFila}>
            Añadir línea
          </Button>
          <Typography variant="subtitle1" data-testid="total-factura">
            Total: {formatearImporte(totalFactura)} €
          </Typography>
        </Stack>
      </Paper>

      <Button
        variant="contained"
        data-testid="guardar-factura"
        disabled={guardando || !valido || !ejercicioAbierto}
        onClick={guardar}
      >
        Registrar factura
      </Button>

      {msg && (
        <Alert severity="success" sx={{ mt: 2 }} data-testid="mensaje">
          {msg}
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }} data-testid="error">
          {error}
        </Alert>
      )}
    </div>
  );
}
