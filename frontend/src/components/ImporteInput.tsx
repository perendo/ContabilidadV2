"use client";

import { useState } from "react";

import { formatearImporte, parsearImporte } from "@/lib/formato";

interface Props {
  label: string;
  value: string;
  onChange: (valor: string) => void;
}

/**
 * Campo de importe: se muestra y edita en formato europeo (1.255,13), pero
 * entrega el valor en decimal con punto que espera el backend ("1255.13").
 */
export default function ImporteInput({ label, value, onChange }: Props) {
  const [editando, setEditando] = useState<string | null>(null);
  const mostrado = editando ?? (value === "" ? "" : formatearImporte(value));
  return (
    <input
      aria-label={label}
      type="text"
      inputMode="decimal"
      value={mostrado}
      onFocus={() => setEditando(value === "" ? "" : formatearImporte(value))}
      onChange={(e) => {
        setEditando(e.target.value);
        onChange(parsearImporte(e.target.value));
      }}
      onBlur={() => setEditando(null)}
    />
  );
}