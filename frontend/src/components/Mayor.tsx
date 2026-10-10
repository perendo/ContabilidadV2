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
  InputLabel,
  MenuItem,
  FormControl,
  Select,
  Alert,
  CircularProgress,
  Grid,
  Divider,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Chip,
} from "@mui/material";
import {
  Download as DownloadIcon,
  Search as SearchIcon,
  AccountTree as AccountTreeIcon,
  TableChart as TableChartIcon,
} from "@mui/icons-material";
import { api, type MayorCuenta, type FilaMayorCuenta, type MayorGlobal } from "@/lib/api";

export default function Mayor() {
  const [modo, setModo] = useState<"cuenta" | "global">("cuenta");
  const [cuentaInput, setCuentaInput] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [cuentasGlobal, setCuentasGlobal] = useState<FilaMayorCuenta[]>([]);
  const [mayorCuenta, setMayorCuenta] = useState<MayorCuenta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cuentasOptions, setCuentasOptions] = useState<{ value: string; label: string }[]>([]);

  const cargarCuentas = useCallback(async () => {
    try {
      const res = await api.cuentas({ limit: 500 });
      setCuentasOptions(
        res.items.map((c) => ({
          value: c.codigo,
          label: `${c.codigo} - ${c.nombre}`,
        }))
      );
    } catch {
      // silencioso
    }
  }, []);

  useEffect(() => {
    cargarCuentas();
  }, [cargarCuentas]);

  const handleBuscar = async () => {
    if (modo === "cuenta" && !cuentaInput.trim()) {
      setError("Introduce un código de cuenta");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (modo === "cuenta") {
        const data = await api.mayor(cuentaInput.trim(), { desde: desde || undefined, hasta: hasta || undefined });
        setMayorCuenta(data);
      } else {
        const data = await api.mayorCuentas({ desde: desde || undefined, hasta: hasta || undefined });
        setCuentasGlobal(data.cuentas);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al cargar el informe";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleExportar = async (formato: "csv" | "pdf") => {
    if (modo === "cuenta" && !cuentaInput.trim()) {
      setError("Introduce un código de cuenta");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (modo === "cuenta") {
        await api.descargarInforme("mayor", formato, {
          cuenta: cuentaInput.trim(),
          desde: desde || undefined,
          hasta: hasta || undefined,
        });
      } else {
        await api.descargarInforme("balance", formato, {
          desde: desde || undefined,
          hasta: hasta || undefined,
        });
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al exportar";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleNavegarDetalle = (codigo: string) => {
    setCuentaInput(codigo);
    setModo("cuenta");
    handleBuscar();
  };

  return (
    <Box sx={{ p: 3, maxWidth: "1200px", mx: "auto" }}>
      <Typography variant="h4" gutterBottom>
        Libro Mayor
      </Typography>

      <Tabs value={modo} onChange={(_, v) => setModo(v as "cuenta" | "global")} sx={{ mb: 3 }}>
        <Tab value="cuenta" icon={<TableChartIcon />} label="Mayor de cuenta" />
        <Tab value="global" icon={<AccountTreeIcon />} label="Listado global" />
      </Tabs>

      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="flex-end">
          {modo === "cuenta" && (
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel id="cuenta-label">Cuenta</InputLabel>
                <Select
                  labelId="cuenta-label"
                  value={cuentaInput}
                  label="Cuenta"
                  onChange={(e) => setCuentaInput(e.target.value)}
                >
                  {cuentasOptions.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          )}
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
              startIcon={<SearchIcon />}
              onClick={handleBuscar}
              disabled={loading}
            >
              Consultar
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {modo === "cuenta" ? (
        mayorCuenta ? (
          <>
            <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item>
                  <Typography variant="h6" gutterBottom>
                    {mayorCuenta.cuenta.codigo} - {mayorCuenta.cuenta.nombre}
                  </Typography>
                </Grid>
                <Grid item>
                  <Typography color="text.secondary">
                    Saldo inicial: <strong>{mayorCuenta.saldo_inicial}</strong>
                  </Typography>
                </Grid>
                <Grid item>
                  <Typography color="text.secondary">
                    Total Debe: <strong>{mayorCuenta.total_debe}</strong>
                  </Typography>
                </Grid>
                <Grid item>
                  <Typography color="text.secondary">
                    Total Haber: <strong>{mayorCuenta.total_haber}</strong>
                  </Typography>
                </Grid>
                <Grid item>
                  <Typography color="text.secondary" sx={{ fontWeight: "bold" }}>
                    Saldo final: <strong>{mayorCuenta.saldo_final}</strong>
                  </Typography>
                </Grid>
                <Grid item>
                  <Box sx={{ display: "flex", gap: 1 }}>
                    <Tooltip title="Exportar CSV">
                      <IconButton
                        onClick={() => handleExportar("csv")}
                        disabled={loading}
                        aria-label="Exportar CSV"
                      >
                        <DownloadIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Exportar PDF">
                      <IconButton
                        onClick={() => handleExportar("pdf")}
                        disabled={loading}
                        aria-label="Exportar PDF"
                      >
                        <DownloadIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Grid>
              </Grid>
            </Paper>

            {mayorCuenta.movimientos.length === 0 ? (
              <Alert severity="info">La cuenta no tiene movimientos en el periodo seleccionado.</Alert>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Fecha</TableCell>
                      <TableCell align="center">Nº</TableCell>
                      <TableCell>Concepto</TableCell>
                      <TableCell align="right">Debe</TableCell>
                      <TableCell align="right">Haber</TableCell>
                      <TableCell align="right">Saldo</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {mayorCuenta.movimientos.map((mov, idx) => (
                      <TableRow key={idx} hover>
                        <TableCell>{mov.fecha}</TableCell>
                        <TableCell align="center">{mov.numero}</TableCell>
                        <TableCell>{mov.concepto}</TableCell>
                        <TableCell align="right">{mov.debe}</TableCell>
                        <TableCell align="right">{mov.haber}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 500 }}>
                          {mov.saldo}
                        </TableCell>
                      </TableRow>
                    ))}
                    <TableRow sx={{ fontWeight: "bold", bgColor: "action.hover" }}>
                      <TableCell colSpan={3} align="right">
                        TOTALES
                      </TableCell>
                      <TableCell align="right">{mayorCuenta.total_debe}</TableCell>
                      <TableCell align="right">{mayorCuenta.total_haber}</TableCell>
                      <TableCell align="right">{mayorCuenta.saldo_final}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </>
        ) : (
          <Alert severity="info">Selecciona una cuenta y pulsa Consultar para ver el Mayor.</Alert>
        )
      ) : (
        <>
          <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mb: 2 }}>
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
          {cuentasGlobal.length === 0 ? (
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
                    <TableCell align="right">Saldo</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {cuentasGlobal.map((cuenta, idx) => (
                    <TableRow key={idx} hover onClick={() => handleNavegarDetalle(cuenta.codigo)} style={{ cursor: "pointer" }}>
                      <TableCell sx={{ fontWeight: 500 }}>{cuenta.codigo}</TableCell>
                      <TableCell>{cuenta.nombre}</TableCell>
                      <TableCell align="center">{cuenta.nivel}</TableCell>
                      <TableCell align="right">{cuenta.suma_debe}</TableCell>
                      <TableCell align="right">{cuenta.suma_haber}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 500 }}>
                        {cuenta.saldo}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={cuenta.saldo_tipo}
                          size="small"
                          color={
                            cuenta.saldo_tipo === "deudor"
                              ? "success"
                              : cuenta.saldo_tipo === "acreedor"
                              ? "error"
                              : "default"
                          }
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Ver detalle">
                          <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleNavegarDetalle(cuenta.codigo); }}>
                            <SearchIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </>
      )}

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", my: 4 }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
}