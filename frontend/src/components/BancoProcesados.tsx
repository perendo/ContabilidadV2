"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { ApiError, api, type LogProcesamiento } from "@/lib/api";
import { useCargar } from "@/lib/useCargar";

function parseJson(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

function reglasTexto(reglas: unknown): string {
  if (Array.isArray(reglas)) return reglas.length ? `IDs: ${reglas.join(", ")}` : "—";
  return String(reglas ?? "—");
}

export default function BancoProcesados() {
  const logsQ = useCargar(() => api.banco.logs(), []);
  const [ver, setVer] = useState<LogProcesamiento | null>(null);

  const logs = logsQ.data ?? [];

  return (
    <Box>
      {logsQ.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {logsQ.error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small" aria-label="Historial de procesamientos">
          <TableHead>
            <TableRow>
              <TableCell>Fecha</TableCell>
              <TableCell align="right">Creados</TableCell>
              <TableCell align="right">Pendientes</TableCell>
              <TableCell align="right">Fallidos</TableCell>
              <TableCell>Reglas aplicadas</TableCell>
              <TableCell align="right">Detalle</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logs.length === 0 && !logsQ.loading && (
              <TableRow>
                <TableCell colSpan={6}>Sin procesamientos todavía.</TableCell>
              </TableRow>
            )}
            {logs.map((l) => {
              const fallidos = parseJson(l.fallidos_json);
              const nFallidos = Array.isArray(fallidos) ? fallidos.length : 0;
              return (
                <TableRow key={l.id}>
                  <TableCell>{new Date(l.timestamp).toLocaleString("es-ES")}</TableCell>
                  <TableCell align="right">{l.creados}</TableCell>
                  <TableCell align="right">{l.pendientes}</TableCell>
                  <TableCell align="right">
                    {nFallidos > 0 ? (
                      <Chip size="small" color="error" label={nFallidos} />
                    ) : (
                      0
                    )}
                  </TableCell>
                  <TableCell>{reglasTexto(parseJson(l.reglas_aplicadas_json))}</TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => setVer(l)}>
                      Ver log
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={!!ver} onClose={() => setVer(null)} maxWidth="md" fullWidth>
        <DialogTitle>Detalle del procesamiento</DialogTitle>
        <DialogContent>
          {ver && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 1 }}>
              <Typography variant="body2">
                <strong>Fecha:</strong>{" "}
                {new Date(ver.timestamp).toLocaleString("es-ES")}
              </Typography>
              <Typography variant="body2">
                <strong>Usuario:</strong> {ver.usuario_id}
              </Typography>
              <Typography variant="body2">
                <strong>Creados:</strong> {ver.creados} · <strong>Pendientes:</strong>{" "}
                {ver.pendientes}
              </Typography>
              <Typography variant="body2">
                <strong>Reglas aplicadas:</strong>
              </Typography>
              <pre style={{ margin: 0 }}>
                {JSON.stringify(parseJson(ver.reglas_aplicadas_json), null, 2)}
              </pre>
              <Typography variant="body2">
                <strong>Fallidos:</strong>
              </Typography>
              <pre style={{ margin: 0 }}>
                {JSON.stringify(parseJson(ver.fallidos_json), null, 2)}
              </pre>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
}