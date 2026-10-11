"use client";

import { useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { Article, Description, TableChart } from "@mui/icons-material";

import { ApiError, api, type ImportResponse } from "@/lib/api";

type FormatoCliente = "excel" | "csv" | "csb" | "auto";

function detectarFormato(nombre: string): FormatoCliente {
  const ext = nombre.toLowerCase().split(".").pop() ?? "";
  if (["xlsx", "xls"].includes(ext)) return "excel";
  if (ext === "csv") return "csv";
  if (["csb", "txt", "43"].includes(ext)) return "csb";
  return "auto";
}

const ETIQUETAS_FORMATO: Record<FormatoCliente, string> = {
  excel: "Excel Santander",
  csv: "CSV estándar",
  csb: "CSB / Cuaderno 43",
  auto: "Detección automática",
};

async function leerTexto(archivo: File): Promise<string> {
  if (typeof archivo.text === "function") return archivo.text();
  return new Promise((resolve, reject) => {
    const lector = new FileReader();
    lector.onload = () => resolve(String(lector.result ?? ""));
    lector.onerror = () => reject(lector.error);
    lector.readAsText(archivo);
  });
}

/** Vista previa: primeras 20 filas de un CSV/CSB (columnas separadas por `;`). */
function filasPreview(texto: string): string[][] {
  return texto
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, 21)
    .map((l) => l.split(";"));
}

export default function BancoImportar() {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [ignorar, setIgnorar] = useState(false);
  const [preview, setPreview] = useState<string[][] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState<ImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function seleccionar(f: File | null) {
    setArchivo(f);
    setResultado(null);
    setError(null);
    if (!f) {
      setPreview(null);
      return;
    }
    if (detectarFormato(f.name) === "excel") {
      setPreview(null);
      return;
    }
    try {
      setPreview(filasPreview(await leerTexto(f)));
    } catch {
      setPreview(null);
    }
  }

  async function importar() {
    if (!archivo) return;
    setCargando(true);
    setError(null);
    setResultado(null);
    try {
      setResultado(await api.banco.importar(archivo, ignorar));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al importar el extracto");
    } finally {
      setCargando(false);
    }
  }

  const formato = archivo ? detectarFormato(archivo.name) : null;

  return (
    <Box>
      <Paper
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          seleccionar(e.dataTransfer.files?.[0] ?? null);
        }}
        onClick={() => inputRef.current?.click()}
        sx={{
          p: 4,
          mb: 2,
          textAlign: "center",
          border: arrastrando ? "2px dashed" : "1px dashed",
          borderColor: arrastrando ? "primary.main" : "divider",
          cursor: "pointer",
        }}
        data-testid="zona-drop"
      >
        <Typography variant="h6" gutterBottom>
          Importar extracto bancario
        </Typography>
        <Typography color="text.secondary" gutterBottom>
          Arrastra el archivo aquí o haz clic para seleccionarlo (Excel Santander, CSV estándar o
          CSB / Cuaderno 43).
        </Typography>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv,.csb,.txt"
          style={{ display: "none" }}
          aria-label="Seleccionar archivo"
          onChange={(e) => seleccionar(e.target.files?.[0] ?? null)}
        />
      </Paper>

      {archivo && formato && (
        <Box sx={{ mb: 2 }}>
          <Chip
            icon={
              formato === "excel" ? <Description /> : formato === "csb" ? <Article /> : <TableChart />
            }
            label={`${archivo.name} · ${ETIQUETAS_FORMATO[formato]}`}
          />
        </Box>
      )}

      {preview && (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ p: 1 }}>
            Vista previa (primeras {Math.min(preview.length - 1, 20)} filas de datos)
          </Typography>
          <Table size="small" aria-label="Vista previa del extracto">
            <TableHead>
              <TableRow>
                {(preview[0] ?? []).map((col, i) => (
                  <TableCell key={i}>{col || `Col ${i + 1}`}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {preview.slice(1).map((fila, i) => (
                <TableRow key={i}>
                  {fila.map((celda, j) => (
                    <TableCell key={j}>{celda}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {archivo && !preview && formato === "excel" && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Los archivos Excel no admiten vista previa en el navegador; se importarán directamente.
        </Alert>
      )}

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <Button variant="contained" disabled={!archivo || cargando} onClick={importar}>
          {cargando ? <CircularProgress size={20} /> : "Importar"}
        </Button>
        <FormControlLabel
          control={
            <Checkbox checked={ignorar} onChange={(e) => setIgnorar(e.target.checked)} />
          }
          label="Ignorar duplicados"
        />
      </Box>

      {resultado && (
        <Alert
          severity={resultado.importados > 0 || resultado.duplicados > 0 ? "success" : "warning"}
          sx={{ mb: 2 }}
        >
          {resultado.importados} movimientos importados · {resultado.duplicados} duplicados
          {resultado.errores.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {resultado.errores.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
    </Box>
  );
}