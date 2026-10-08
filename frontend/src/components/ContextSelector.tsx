"use client";

import { useEffect, useState } from "react";
import { MenuItem, Stack, TextField, Toolbar } from "@mui/material";

import {
  api,
  type Ejercicio,
  type Empresa,
  getEjercicioId,
  getEmpresaId,
  setEjercicioId,
  setEmpresaId,
} from "@/lib/api";

export default function ContextSelector() {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [ejercicios, setEjercicios] = useState<Ejercicio[]>([]);
  const [empresaId, setEmpresa] = useState<string>("");
  const [ejercicioId, setEjercicio] = useState<string>("");

  useEffect(() => {
    let activo = true;
    api
      .empresas()
      .then((lista) => {
        if (!activo) return;
        setEmpresas(lista);
        const ultimaEmpresa = getEmpresaId();
        const elegida =
          ultimaEmpresa && lista.some((e) => String(e.id) === ultimaEmpresa)
            ? ultimaEmpresa
            : lista[0]
              ? String(lista[0].id)
              : "";
        if (elegida) {
          setEmpresa(elegida);
          setEmpresaId(elegida);
        }
      })
      .catch(() => undefined);
    return () => {
      activo = false;
    };
  }, []);

  useEffect(() => {
    if (!empresaId) {
      setEjercicios([]);
      return;
    }
    let activo = true;
    setEmpresaId(empresaId);
    api
      .ejercicios()
      .then((lista) => {
        if (!activo) return;
        setEjercicios(lista);
        const ultimoEjercicio = getEjercicioId();
        const elegido =
          ultimoEjercicio && lista.some((e) => String(e.id) === ultimoEjercicio)
            ? ultimoEjercicio
            : lista[0]
              ? String(lista[0].id)
              : "";
        if (elegido) {
          setEjercicio(elegido);
          setEjercicioId(elegido);
        }
      })
      .catch(() => undefined);
    return () => {
      activo = false;
    };
  }, [empresaId]);

  return (
    <Toolbar component="header" data-testid="context-selector" sx={{ gap: 2 }}>
      <Stack direction="row" spacing={2} sx={{ flexGrow: 1 }}>
        <TextField
          select
          size="small"
          label="Empresa"
          value={empresaId}
          onChange={(e) => setEmpresa(e.target.value)}
          sx={{ minWidth: 220 }}
          data-testid="selector-empresa"
        >
          {empresas.map((e) => (
            <MenuItem key={e.id} value={String(e.id)}>
              {e.nombre_comercial || e.razon_social}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label="Ejercicio"
          value={ejercicioId}
          onChange={(e) => setEjercicio(e.target.value)}
          sx={{ minWidth: 140 }}
          data-testid="selector-ejercicio"
        >
          {ejercicios.map((e) => (
            <MenuItem key={e.id} value={String(e.id)}>
              {e.anio} ({e.estado})
            </MenuItem>
          ))}
        </TextField>
      </Stack>
    </Toolbar>
  );
}