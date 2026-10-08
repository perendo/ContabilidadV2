"use client";

import { useState } from "react";
import { Box, Button, CircularProgress, TextField, Typography } from "@mui/material";
import { useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.login(username, password);
      router.replace("/seleccion");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      sx={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Box
        component="form"
        onSubmit={enviar}
        sx={{ display: "flex", flexDirection: "column", gap: 2, width: 320 }}
        data-testid="login-form"
      >
        <Typography variant="h5" gutterBottom>
          ContabilidadV2
        </Typography>
        <TextField
          label="Usuario"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <TextField
          label="Contraseña"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <Typography color="error">{error}</Typography>}
        <Button type="submit" variant="contained" disabled={loading} startIcon={loading && <CircularProgress size={18} />}>
          Iniciar sesión
        </Button>
      </Box>
    </Box>
  );
}