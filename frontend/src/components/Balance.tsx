"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Box,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Alert,
  CircularProgress,
  Grid,
  IconButton,
  Tooltip,
  Chip,
} from "@mui/material";
import { Download as DownloadIcon } from "@mui/icons-material";
import { api, type Balance, type FilaBalance } from "@/lib/api";

export default function Balance() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [balance, setBalance] = useState<Balance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBuscar = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.balance({ desde: desde || undefined, hasta: hasta || undefined });
      setBalance(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al cargar el informe";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleExportar = async (formato: "csv" | "pdf") => {
    setLoading(true);
    setError(null);
    try {
      await api.descargarInforme("balance", formato, { desde: desde || undefined, hasta: hasta || undefined });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al exportar";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: "1200px", mx: "auto" }}>
      <Typography variant="h4" gutterBottom>
        Balance de Sumas y Saldos
      </Typography>

      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="flex-end">
          <Grid item xs={12} sm={3}>
            <TextField
              fullWidth
              size="small"
              type="date"
              label="Desde"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              InputProps={{
                inputProps: { max: hasta || undefined },
              }}
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              fullWidth
              size="small"
              type="date"
              label="Hasta"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              InputProps={{
                inputProps: { min: desde || undefined },
              }}
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleBuscar}
              disabled={loading}
            >
              Consultar
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {balance ? (
        <>
          <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item>
                <Typography color="text.secondary">
                  Total Debe: <strong>{balance.total_debe}</strong>
                </Typography>
              </Grid>
              <Grid item>
                <Typography color="text.secondary">
                  Total Haber: <strong>{balance.total_haber}</strong>
                </Typography>
              </Grid>
              <Grid item>
                <Typography color="text.secondary">
                  Total Saldo Deudor: <strong>{balance.total_saldo_deudor}</strong>
                </Typography>
              </Grid>
              <Grid item>
                <Typography color="text.secondary">
                  Total Saldo Acreedor: <strong>{balance.total_saldo_acreedor}</strong>
                </Typography>
              </Grid>
              <Grid item>
                <Typography
                  color={balance.cuadra ? "success.main" : "error.main"}
                  sx={{ fontWeight: "bold" }}
                >
                  Cuadre: {balance.cuadra ? "✓ Cuadra (ΣDebe = ΣHaber)" : "✗ No cuadra"}
                </Typography>
              </Grid>
              <Grid item>
                <Box sx={{ display: "flex", gap: 1 }}>
                  <Tooltip title="Exportar CSV">
                    <IconButton onClick={() => handleExportar("csv")} disabled={loading} aria-label="Exportar CSV">
                      <DownloadIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Exportar PDF">
                    <IconButton onClick={() => handleExportar("pdf")} disabled={loading} aria-label="Exportar PDF">
                      <DownloadIcon />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Grid>
            </Grid>
          </Paper>

          {balance.filas.length === 0 ? (
            <Alert severity="info">No hay cuentas con movimiento en el periodo seleccionado.</Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Código</TableCell>
                    <TableCell>Nombre</TableCell>
                    <TableCell align="center">Nivel</TableCell>
                    <TableCell align="right">Suma Debe</TableCell>
                    <TableCell align="right">Suma Haber</TableCell>
                    <TableCell align="right">Saldo Deudor</TableCell>
                    <TableCell align="right">Saldo Acreedor</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {balance.filas.map((fila, idx) => (
                    <TableRow key={idx} hover sx={{ fontWeight: fila.nivel <= 3 ? 600 : 400 }}>
                      <TableCell sx={{ fontWeight: fila.nivel <= 3 ? 600 : 400 }}>
                        {fila.codigo}
                      </TableCell>
                      <TableCell sx={{ pl: fila.nivel }}>
                        {fila.nombre}
                      </TableCell>
                      <TableCell align="center">{fila.nivel}</TableCell>
                      <TableCell align="right">{fila.suma_debe}</TableCell>
                      <TableCell align="right">{fila.suma_haber}</TableCell>
                      <TableCell align="right">{fila.saldo_deudor}</TableCell>
                      <TableCell align="right">{fila.saldo_acreedor}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow sx={{ fontWeight: "bold", bgColor: "action.hover" }}>
                    <TableCell colSpan={3} align="right">TOTALES</TableCell>
                    <TableCell align="right">{balance.total_debe}</TableCell>
                    <TableCell align="right">{balance.total_haber}</TableCell>
                    <TableCell align="right">{balance.total_saldo_deudor}</TableCell>
                    <TableCell align="right">{balance.total_saldo_acreedor}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </>
      ) : (
        <Alert severity="info">Selecciona un rango de fechas y pulsa Consultar para ver el Balance.</Alert>
      )}

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", my: 4 }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
}