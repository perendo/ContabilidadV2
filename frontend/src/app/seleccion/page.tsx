"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useRouter } from "next/navigation";

import {
  api,
  ApiError,
  getEmpresaId,
  getEjercicioId,
  setEmpresaId,
  setEjercicioId,
  type Ejercicio,
  type Empresa,
  type UsuarioPerfil,
} from "@/lib/api";

export default function SeleccionContexto() {
  const router = useRouter();
  const anioActual = new Date().getFullYear();

  const [perfil, setPerfil] = useState<UsuarioPerfil | null>(null);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [ejercicios, setEjercicios] = useState<Ejercicio[]>([]);
  const [empresaSel, setEmpresaSel] = useState<number | null>(null);
  const [ejercicioSel, setEjercicioSel] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [ocupado, setOcupado] = useState(false);

  const [creandoEmpresa, setCreandoEmpresa] = useState(false);
  const [nuevaEmpresa, setNuevaEmpresa] = useState({
    cif: "",
    razon_social: "",
    nombre_comercial: "",
  });

  const [creandoEjercicio, setCreandoEjercicio] = useState(false);
  const [nuevoEjercicio, setNuevoEjercicio] = useState({
    anio: anioActual,
    fecha_inicio: `${anioActual}-01-01`,
    fecha_fin: `${anioActual}-12-31`,
  });

  const esAdmin = perfil?.rol === "admin";

  useEffect(() => {
    let activo = true;
    (async () => {
      try {
        const [p, emps] = await Promise.all([api.me(), api.empresas()]);
        if (!activo) return;
        setPerfil(p);
        setEmpresas(emps);
        const cookieEmpresa = Number(getEmpresaId());
        if (cookieEmpresa && emps.some((e) => e.id === cookieEmpresa)) {
          setEmpresaSel(cookieEmpresa);
        }
        if (emps.length === 0) setCreandoEmpresa(true);
      } catch (err) {
        if (activo) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar la información");
        }
      } finally {
        if (activo) setCargando(false);
      }
    })();
    return () => {
      activo = false;
    };
  }, []);

  useEffect(() => {
    if (!empresaSel) {
      setEjercicios([]);
      setEjercicioSel(null);
      return;
    }
    let activo = true;
    setEmpresaId(empresaSel);
    (async () => {
      try {
        const ejs = await api.ejercicios();
        if (!activo) return;
        setEjercicios(ejs);
        const cookieEjercicio = Number(getEjercicioId());
        const preferido = ejs.find((e) => e.id === cookieEjercicio) ?? ejs[0];
        setEjercicioSel(preferido ? preferido.id : null);
        if (ejs.length === 0) setCreandoEjercicio(true);
      } catch (err) {
        if (activo) {
          setError(err instanceof ApiError ? err.message : "No se pudieron cargar los ejercicios");
        }
      }
    })();
    return () => {
      activo = false;
    };
  }, [empresaSel]);

  async function crearEmpresa(e: React.FormEvent) {
    e.preventDefault();
    setOcupado(true);
    setError(null);
    try {
      const empresa = await api.crearEmpresa({
        cif: nuevaEmpresa.cif.trim().toUpperCase(),
        razon_social: nuevaEmpresa.razon_social.trim(),
        nombre_comercial: nuevaEmpresa.nombre_comercial.trim() || null,
      });
      setEmpresas((prev) => [...prev, empresa]);
      setEmpresaSel(empresa.id);
      setCreandoEmpresa(false);
      setNuevaEmpresa({ cif: "", razon_social: "", nombre_comercial: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la empresa");
    } finally {
      setOcupado(false);
    }
  }

  async function crearEjercicio(e: React.FormEvent) {
    e.preventDefault();
    if (!empresaSel) return;
    setOcupado(true);
    setError(null);
    try {
      const ejercicio = await api.crearEjercicio({
        anio: Number(nuevoEjercicio.anio),
        fecha_inicio: nuevoEjercicio.fecha_inicio,
        fecha_fin: nuevoEjercicio.fecha_fin,
      });
      setEjercicios((prev) => [...prev, ejercicio]);
      setEjercicioSel(ejercicio.id);
      setCreandoEjercicio(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el ejercicio");
    } finally {
      setOcupado(false);
    }
  }

  function entrar() {
    if (!empresaSel || !ejercicioSel) return;
    setEmpresaId(empresaSel);
    setEjercicioId(ejercicioSel);
    router.replace("/");
  }

  return (
    <Box sx={{ maxWidth: 720, mx: "auto", mt: 4 }} data-testid="seleccion-contexto">
      <Typography variant="h5" gutterBottom>
        Selecciona o crea tu empresa y ejercicio
      </Typography>
      <Typography color="text.secondary" gutterBottom>
        Necesitas elegir una empresa y un ejercicio contable para operar.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ my: 2 }}>
          {error}
        </Alert>
      )}

      {cargando ? (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Stack spacing={3} sx={{ mt: 2 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              1. Empresa
            </Typography>

            {empresas.length > 0 && (
              <List dense sx={{ mb: 1 }}>
                {empresas.map((e) => (
                  <ListItemButton
                    key={e.id}
                    selected={e.id === empresaSel}
                    onClick={() => setEmpresaSel(e.id)}
                  >
                    <ListItemText
                      primary={e.razon_social}
                      secondary={`${e.cif}${e.nombre_comercial ? ` · ${e.nombre_comercial}` : ""}`}
                    />
                  </ListItemButton>
                ))}
              </List>
            )}

            {esAdmin ? (
              creandoEmpresa ? (
                <Box
                  component="form"
                  onSubmit={crearEmpresa}
                  sx={{ display: "flex", flexDirection: "column", gap: 2 }}
                >
                  <Divider />
                  <TextField
                    label="CIF (9 caracteres)"
                    value={nuevaEmpresa.cif}
                    onChange={(e) => setNuevaEmpresa((v) => ({ ...v, cif: e.target.value }))}
                    inputProps={{ maxLength: 9 }}
                    required
                  />
                  <TextField
                    label="Razón social"
                    value={nuevaEmpresa.razon_social}
                    onChange={(e) =>
                      setNuevaEmpresa((v) => ({ ...v, razon_social: e.target.value }))
                    }
                    required
                  />
                  <TextField
                    label="Nombre comercial (opcional)"
                    value={nuevaEmpresa.nombre_comercial}
                    onChange={(e) =>
                      setNuevaEmpresa((v) => ({ ...v, nombre_comercial: e.target.value }))
                    }
                  />
                  <Stack direction="row" spacing={1}>
                    <Button type="submit" variant="contained" disabled={ocupado}>
                      Crear empresa
                    </Button>
                    {empresas.length > 0 && (
                      <Button onClick={() => setCreandoEmpresa(false)} disabled={ocupado}>
                        Cancelar
                      </Button>
                    )}
                  </Stack>
                </Box>
              ) : (
                <Button onClick={() => setCreandoEmpresa(true)}>+ Crear empresa</Button>
              )
            ) : (
              <Alert severity="info">
                Solo un usuario <strong>admin</strong> puede crear empresas. Pide a un admin que cree
                una empresa o te asigne a una existente.
              </Alert>
            )}
          </Paper>

          <Paper variant="outlined" sx={{ p: 2, opacity: empresaSel ? 1 : 0.5 }}>
            <Typography variant="h6" gutterBottom>
              2. Ejercicio
            </Typography>

            {!empresaSel ? (
              <Typography color="text.secondary">Selecciona primero una empresa.</Typography>
            ) : (
              <>
                {ejercicios.length > 0 && (
                  <List dense sx={{ mb: 1 }}>
                    {ejercicios.map((e) => (
                      <ListItemButton
                        key={e.id}
                        selected={e.id === ejercicioSel}
                        onClick={() => setEjercicioSel(e.id)}
                      >
                        <ListItemText
                          primary={`Ejercicio ${e.anio}`}
                          secondary={`${e.fecha_inicio} → ${e.fecha_fin} · ${e.estado}`}
                        />
                      </ListItemButton>
                    ))}
                  </List>
                )}

                {creandoEjercicio ? (
                  <Box
                    component="form"
                    onSubmit={crearEjercicio}
                    sx={{ display: "flex", flexDirection: "column", gap: 2 }}
                  >
                    <Divider />
                    <TextField
                      label="Año"
                      type="number"
                      value={nuevoEjercicio.anio}
                      onChange={(e) =>
                        setNuevoEjercicio((v) => ({ ...v, anio: Number(e.target.value) }))
                      }
                      inputProps={{ min: 2000, max: 2100 }}
                      required
                    />
                    <TextField
                      label="Fecha de inicio"
                      type="date"
                      InputLabelProps={{ shrink: true }}
                      value={nuevoEjercicio.fecha_inicio}
                      onChange={(e) =>
                        setNuevoEjercicio((v) => ({ ...v, fecha_inicio: e.target.value }))
                      }
                      required
                    />
                    <TextField
                      label="Fecha de fin"
                      type="date"
                      InputLabelProps={{ shrink: true }}
                      value={nuevoEjercicio.fecha_fin}
                      onChange={(e) =>
                        setNuevoEjercicio((v) => ({ ...v, fecha_fin: e.target.value }))
                      }
                      required
                    />
                    <Stack direction="row" spacing={1}>
                      <Button type="submit" variant="contained" disabled={ocupado}>
                        Crear ejercicio
                      </Button>
                      {ejercicios.length > 0 && (
                        <Button onClick={() => setCreandoEjercicio(false)} disabled={ocupado}>
                          Cancelar
                        </Button>
                      )}
                    </Stack>
                  </Box>
                ) : (
                  <Button onClick={() => setCreandoEjercicio(true)}>+ Crear ejercicio</Button>
                )}
              </>
            )}
          </Paper>

          <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
            <Button
              variant="contained"
              size="large"
              disabled={!empresaSel || !ejercicioSel}
              onClick={entrar}
            >
              Entrar
            </Button>
          </Box>
        </Stack>
      )}
    </Box>
  );
}
