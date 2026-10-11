"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  IconButton,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";

import {
  ApiError,
  api,
  type AjusteIS,
  type LiquidacionISIn,
  type LiquidacionISOut,
} from "@/lib/api";
import { formatearImporte } from "@/lib/formato";
import { useCargar } from "@/lib/useCargar";

interface AjusteFila {
  id: number;
  concepto: string;
  sentido: "aumento" | "disminucion";
  importe: string;
}

export default function LiquidacionIS() {
  const [resultado, setResultado] = useState("0");
  const [tipo, setTipo] = useState("25");
  const [retenciones, setRetenciones] = useState("0");
  const [ajustes, setAjustes] = useState<AjusteFila[]>([]);
  const [nextId, setNextId] = useState(1);
  const [accion, setAccion] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);

  const {
    data,
    loading,
    error: errorCarga,
    setData,
  } = useCargar<LiquidacionISOut | null>(async () => {
    try {
      return await api.impuestoSociedades.obtener();
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  }, []);

  function construirPayload(): LiquidacionISIn {
    return {
      resultado_contable: resultado,
      tipo_gravamen: tipo,
      retenciones_pagos_cuenta: retenciones,
      ajustes: ajustes.map(
        (a): AjusteIS => ({ concepto: a.concepto, sentido: a.sentido, importe: a.importe })
      ),
    };
  }

  function anadirAjuste() {
    setAjustes((prev) => [
      ...prev,
      { id: nextId, concepto: "", sentido: "aumento", importe: "0" },
    ]);
    setNextId((n) => n + 1);
  }

  function actualizarAjuste(id: number, campo: keyof AjusteFila, valor: string) {
    setAjustes((prev) => prev.map((a) => (a.id === id ? { ...a, [campo]: valor } : a)));
  }

  async function crear() {
    setAccion(true);
    setError(null);
    try {
      setData(await api.impuestoSociedades.crear(construirPayload()));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al crear la liquidación");
    } finally {
      setAccion(false);
    }
  }

  async function guardarCambios() {
    setAccion(true);
    setError(null);
    try {
      setData(await api.impuestoSociedades.actualizar(construirPayload()));
      setEditando(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al actualizar la liquidación");
    } finally {
      setAccion(false);
    }
  }

  async function cerrar() {
    setAccion(true);
    setError(null);
    try {
      setData(await api.impuestoSociedades.cerrar());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al cerrar la liquidación");
    } finally {
      setAccion(false);
    }
  }

  function empezarEdicion() {
    if (!data) return;
    setResultado(data.resultado_contable);
    setTipo(data.tipo_gravamen);
    setRetenciones(data.retenciones_pagos_cuenta);
    setAjustes(
      data.ajustes.map((a, i) => ({
        id: i + 1,
        concepto: a.concepto,
        sentido: a.sentido,
        importe: a.importe,
      }))
    );
    setNextId(data.ajustes.length + 1);
    setError(null);
    setEditando(true);
  }

  if (loading) return <Skeleton variant="rectangular" height={200} />;
  if (errorCarga) return <Typography color="error">{errorCarga}</Typography>;

  const mostrarFormulario = !data || editando;

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {mostrarFormulario ? (
        <Box data-testid={editando ? "form-liq-edit" : "form-liq"}>
          <Typography variant="h6" gutterBottom>
            {editando
              ? "Editar liquidación del Impuesto sobre Sociedades"
              : "Nueva liquidación del Impuesto sobre Sociedades"}
          </Typography>
          <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap">
            <TextField
              label="Resultado contable"
              value={resultado}
              onChange={(e) => setResultado(e.target.value)}
              inputProps={{ "data-testid": "resultado", inputMode: "decimal" }}
            />
            <TextField
              label="Tipo de gravamen (%)"
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
              inputProps={{ inputMode: "decimal" }}
            />
            <TextField
              label="Retenciones y pagos a cuenta"
              value={retenciones}
              onChange={(e) => setRetenciones(e.target.value)}
              inputProps={{ inputMode: "decimal" }}
            />
          </Stack>

          <Typography variant="subtitle2" gutterBottom>
            Ajustes al resultado contable
          </Typography>
          {ajustes.map((a) => (
            <Stack key={a.id} direction="row" spacing={1} sx={{ mb: 1 }} alignItems="center">
              <TextField
                label="Concepto"
                size="small"
                value={a.concepto}
                onChange={(e) => actualizarAjuste(a.id, "concepto", e.target.value)}
              />
              <TextField
                select
                label="Sentido"
                size="small"
                value={a.sentido}
                onChange={(e) => actualizarAjuste(a.id, "sentido", e.target.value)}
                sx={{ width: 160 }}
              >
                <MenuItem value="aumento">Aumento</MenuItem>
                <MenuItem value="disminucion">Disminución</MenuItem>
              </TextField>
              <TextField
                label="Importe"
                size="small"
                value={a.importe}
                onChange={(e) => actualizarAjuste(a.id, "importe", e.target.value)}
                inputProps={{ inputMode: "decimal" }}
              />
              <IconButton
                size="small"
                aria-label={`quitar-ajuste-${a.id}`}
                onClick={() => setAjustes((prev) => prev.filter((x) => x.id !== a.id))}
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Stack>
          ))}
          <Button
            size="small"
            startIcon={<AddCircleOutlineIcon />}
            onClick={anadirAjuste}
            sx={{ mb: 2 }}
          >
            Añadir ajuste
          </Button>

          <Stack direction="row" spacing={2}>
            {editando ? (
              <>
                <Button
                  variant="contained"
                  disabled={accion}
                  onClick={guardarCambios}
                  data-testid="guardar-liq"
                >
                  Guardar cambios
                </Button>
                <Button disabled={accion} onClick={() => setEditando(false)}>
                  Cancelar
                </Button>
              </>
            ) : (
              <Button
                variant="contained"
                disabled={accion}
                onClick={crear}
                data-testid="crear-liq"
              >
                Crear liquidación
              </Button>
            )}
          </Stack>
        </Box>
      ) : (
        <Box data-testid="liq-existente">
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">Liquidación del ejercicio</Typography>
            <Chip
              label={data.estado === "cerrada" ? "Cerrada" : "Borrador"}
              color={data.estado === "cerrada" ? "success" : "default"}
              size="small"
            />
          </Stack>
          <Paper variant="outlined">
            <Table size="small" data-testid="tabla-liq">
              <TableBody>
                <TableRow>
                  <TableCell>Resultado contable</TableCell>
                  <TableCell align="right">{formatearImporte(data.resultado_contable)}</TableCell>
                </TableRow>
                {data.ajustes.map((a, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      Ajuste · {a.concepto} ({a.sentido})
                    </TableCell>
                    <TableCell align="right">{formatearImporte(a.importe)}</TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell>Base imponible</TableCell>
                  <TableCell align="right" data-testid="base-imponible">
                    {formatearImporte(data.base_imponible)}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Tipo de gravamen (%)</TableCell>
                  <TableCell align="right">{formatearImporte(data.tipo_gravamen)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Cuota íntegra</TableCell>
                  <TableCell align="right">{formatearImporte(data.cuota_integra)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Retenciones y pagos a cuenta</TableCell>
                  <TableCell align="right">
                    {formatearImporte(data.retenciones_pagos_cuenta)}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Cuota diferencial</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }} data-testid="cuota-diferencial">
                    {formatearImporte(data.cuota_diferencial)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Paper>
          {data.estado === "borrador" && (
            <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
              <Button
                variant="contained"
                disabled={accion}
                onClick={cerrar}
                data-testid="cerrar-liq"
              >
                Cerrar liquidación
              </Button>
              <Button variant="outlined" disabled={accion} onClick={empezarEdicion} data-testid="editar-liq">
                Editar
              </Button>
            </Stack>
          )}
          {data.estado === "cerrada" && (
            <Alert severity="info" sx={{ mt: 2 }}>
              La liquidación está cerrada e inmutable. Los importes quedan congelados.
            </Alert>
          )}
        </Box>
      )}
    </Box>
  );
}
