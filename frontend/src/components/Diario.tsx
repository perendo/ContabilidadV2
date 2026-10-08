"use client";

import { Fragment, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Collapse,
  Pagination,
  Skeleton,
  Snackbar,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useRouter } from "next/navigation";

import { ApiError, api, type AsientoDetalle } from "@/lib/api";
import { useCargar } from "@/lib/useCargar";

const LIMIT = 20;

function TablaAsientos({
  cargar,
  editable,
}: {
  cargar: (offset: number) => Promise<import("@/lib/api").Paginado<import("@/lib/api").AsientoResumen>>;
  editable: boolean;
}) {
  const [page, setPage] = useState(1);
  const [abierto, setAbierto] = useState<number | null>(null);
  const [detalle, setDetalle] = useState<AsientoDetalle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const { data, loading, recargar } = useCargar(() => cargar((page - 1) * LIMIT), [page]);

  async function verDetalle(id: number) {
    if (abierto === id) {
      setAbierto(null);
      return;
    }
    setAbierto(id);
    setDetalle(null);
    try {
      setDetalle(await api.asientoDetalle(id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al cargar el detalle");
    }
  }

  async function asentar(id: number) {
    try {
      await api.asentarAsiento(id);
      recargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al asentar");
    }
  }

  if (loading) return <Skeleton variant="rectangular" height={240} />;

  const totalPaginas = data ? Math.max(1, Math.ceil(data.total / LIMIT)) : 1;

  return (
    <Box>
      {data && data.items.length === 0 ? (
        <Typography color="text.secondary">Sin asientos en este ámbito.</Typography>
      ) : (
        <>
          <Table data-testid={editable ? "tabla-borradores" : "tabla-diario"}>
            <TableHead>
              <TableRow>
                <TableCell>Número</TableCell>
                <TableCell>Fecha</TableCell>
                <TableCell>Concepto</TableCell>
                <TableCell align="right">Debe</TableCell>
                <TableCell align="right">Haber</TableCell>
                {editable && <TableCell align="right">Acciones</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.items.map((a) => (
                <Fragment key={a.id}>
                  <TableRow hover sx={{ cursor: "pointer" }} onClick={() => verDetalle(a.id)}>
                    <TableCell>{a.numero ?? "—"}</TableCell>
                    <TableCell>{a.fecha}</TableCell>
                    <TableCell>{a.concepto}</TableCell>
                    <TableCell align="right">{a.total_debe}</TableCell>
                    <TableCell align="right">{a.total_haber}</TableCell>
                    {editable && (
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="small"
                          disabled={a.total_debe !== a.total_haber}
                          onClick={() => asentar(a.id)}
                        >
                          Asentar
                        </Button>
                        <Button
                          size="small"
                          onClick={() => router.push(`/asientos?borrador=${a.id}`)}
                        >
                          Editar
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                  <TableRow>
                    <TableCell colSpan={editable ? 6 : 5} sx={{ py: 0 }}>
                      <Collapse in={abierto === a.id} timeout="auto" unmountOnExit>
                        <Box sx={{ py: 1 }}>
                          {detalle ? (
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Cuenta</TableCell>
                                  <TableCell align="right">Debe</TableCell>
                                  <TableCell align="right">Haber</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {detalle.apuntes.map((p, i) => (
                                  <TableRow key={i}>
                                    <TableCell>{p.cuenta_codigo}</TableCell>
                                    <TableCell align="right">{p.debe}</TableCell>
                                    <TableCell align="right">{p.haber}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          ) : (
                            <Typography variant="body2">Cargando…</Typography>
                          )}
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </Fragment>
              ))}
            </TableBody>
          </Table>
          <Pagination
            sx={{ mt: 2 }}
            count={totalPaginas}
            page={page}
            onChange={(_, p) => setPage(p)}
          />
        </>
      )}

      <Snackbar open={!!error} autoHideDuration={5000} onClose={() => setError(null)}>
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default function Diario() {
  const [tab, setTab] = useState(0);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");

  return (
    <Box>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Diario" />
        <Tab label="Borradores" />
      </Tabs>

      {tab === 0 ? (
        <>
          <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
            <TextField
              label="Desde"
              type="date"
              size="small"
              InputLabelProps={{ shrink: true }}
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
            />
            <TextField
              label="Hasta"
              type="date"
              size="small"
              InputLabelProps={{ shrink: true }}
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
            />
          </Stack>
          <TablaAsientos
            cargar={(offset) =>
              api.diario({
                since: desde || undefined,
                until: hasta || undefined,
                offset,
                limit: LIMIT,
              })
            }
            editable={false}
          />
        </>
      ) : (
        <TablaAsientos cargar={(offset) => api.borradores({ offset, limit: LIMIT })} editable />
      )}
    </Box>
  );
}