"use client";

import { useEffect, useState } from "react";
import {
  AppBar,
  Box,
  Button,
  CircularProgress,
  CssBaseline,
  IconButton,
  Toolbar,
  ThemeProvider,
  Typography,
} from "@mui/material";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import ContextSelector from "@/components/ContextSelector";
import { api, getEmpresaId, getEjercicioId } from "@/lib/api";
import { temaSegunModo } from "@/lib/theme";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [montado, setMontado] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const [oscuro, setOscuro] = useState(false);
  const [estado, setEstado] = useState<"cargando" | "ok" | "anon">("cargando");

  useEffect(() => {
    setMontado(true);
    if (typeof window !== "undefined") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      setOscuro(mq.matches);
      const handler = (e: MediaQueryListEvent) => setOscuro(e.matches);
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, []);

  useEffect(() => {
    if (!montado) return;
    if (pathname === "/login") {
      setEstado("anon");
      return;
    }

    let activo = true;
    setEstado("cargando");

    api
      .me()
      .then(() => {
        if (!activo) return;
        setEstado("ok");
        if ((!getEmpresaId() || !getEjercicioId()) && pathname !== "/seleccion") {
          router.replace("/seleccion");
        }
      })
      .catch(() => {
        if (!activo) return;
        setEstado("anon");
        router.replace("/login");
      });

    return () => {
      activo = false;
    };
  }, [montado, pathname, router]);

  async function salir() {
    try {
      await api.logout();
    } finally {
      router.replace("/login");
    }
  }

  if (!montado) {
    return <>{children}</>;
  }

  const theme = temaSegunModo(oscuro ? "dark" : "light");
  const enLogin = pathname === "/login";
  const enSeleccion = pathname === "/seleccion";
  const tieneContexto = Boolean(getEmpresaId() && getEjercicioId());

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {enLogin || estado === "anon" ? (
        children
      ) : estado === "cargando" || (!enSeleccion && !tieneContexto) ? (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
          <CircularProgress />
        </Box>
      ) : enSeleccion ? (
        <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
          <AppBar position="static" color="default" elevation={1}>
            <Toolbar sx={{ gap: 1 }}>
              <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                ContabilidadV2
              </Typography>
              <IconButton onClick={() => setOscuro((v) => !v)} aria-label="cambiar tema">
                {oscuro ? <LightModeIcon /> : <DarkModeIcon />}
              </IconButton>
              <Button color="inherit" onClick={salir}>
                Salir
              </Button>
            </Toolbar>
          </AppBar>
          <Box component="main" sx={{ p: 3, flexGrow: 1 }}>
            {children}
          </Box>
        </Box>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
          <AppBar position="static" color="default" elevation={1}>
            <ContextSelector />
            <Toolbar sx={{ gap: 1, borderTop: 1, borderColor: "divider" }}>
              <Typography
                component={Link}
                href="/"
                variant="subtitle1"
                sx={{ mr: 2, color: "inherit", textDecoration: "none" }}
              >
                ContabilidadV2
              </Typography>
              <Button component={Link} href="/asientos" color="inherit">
                Asientos
              </Button>
              <Button component={Link} href="/diario" color="inherit">
                Diario
              </Button>
              <Button component={Link} href="/cuentas" color="inherit">
                Plan de cuentas
              </Button>
              <Box sx={{ flexGrow: 1 }} />
              <IconButton onClick={() => setOscuro((v) => !v)} aria-label="cambiar tema">
                {oscuro ? <LightModeIcon /> : <DarkModeIcon />}
              </IconButton>
              <Button color="inherit" onClick={salir}>
                Salir
              </Button>
            </Toolbar>
          </AppBar>
          <Box component="main" sx={{ p: 3, flexGrow: 1 }}>
            {children}
          </Box>
        </Box>
      )}
    </ThemeProvider>
  );
}
