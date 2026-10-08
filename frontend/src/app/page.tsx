"use client";

import { Box, Card, CardActionArea, CardContent, Typography } from "@mui/material";
import Link from "next/link";

const accesos = [
  { href: "/asientos", titulo: "Nuevo asiento", descripcion: "Registra un asiento contable y asiéntalo." },
  { href: "/diario", titulo: "Diario y borradores", descripcion: "Consulta el libro diario y los borradores." },
  { href: "/cuentas", titulo: "Plan de cuentas", descripcion: "Consulta y crea cuentas del ejercicio." },
];

export default function DashboardPage() {
  return (
    <>
      <Typography variant="h4" gutterBottom>
        Panel
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
        {accesos.map((a) => (
          <Card key={a.href} sx={{ width: 300 }}>
            <CardActionArea component={Link} href={a.href}>
              <CardContent>
                <Typography variant="h6">{a.titulo}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {a.descripcion}
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Box>
    </>
  );
}