import { describe, expect, it } from "vitest";

import { formatearImporte, parsearImporte } from "@/lib/formato";

describe("formatearImporte (es-ES)", () => {
  it("usa punto de millares y coma decimal con 2 decimales", () => {
    expect(formatearImporte("1255.13")).toBe("1.255,13");
    expect(formatearImporte("1000000")).toBe("1.000.000,00");
    expect(formatearImporte("0.00")).toBe("0,00");
  });

  it("redondea/rellena a 2 decimales", () => {
    expect(formatearImporte("5")).toBe("5,00");
    expect(formatearImporte("5.5")).toBe("5,50");
  });

  it("devuelve cadena vacía para valores vacíos o nulos", () => {
    expect(formatearImporte("")).toBe("");
    expect(formatearImporte(null)).toBe("");
    expect(formatearImporte(undefined)).toBe("");
  });

  it("conserva el signo en importes negativos", () => {
    expect(formatearImporte("-50.5")).toMatch(/^[-\u2212]50,50$/);
  });
});

describe("parsearImporte (entrada europea -> decimal con punto)", () => {
  it("convierte el formato europeo al decimal del backend", () => {
    expect(parsearImporte("1.255,13")).toBe("1255.13");
    expect(parsearImporte("1.000.000,50")).toBe("1000000.50");
    expect(parsearImporte("0,00")).toBe("0.00");
  });

  it("acepta el punto como decimal cuando no hay coma", () => {
    expect(parsearImporte("1000.00")).toBe("1000.00");
    expect(parsearImporte("1000.5")).toBe("1000.5");
  });

  it("interpreta grupos de 3 dígitos como millares sin coma", () => {
    expect(parsearImporte("1.255")).toBe("1255");
  });

  it("elimina un punto decimal final y espacios", () => {
    expect(parsearImporte("1000.")).toBe("1000");
    expect(parsearImporte("  1.255,13  ")).toBe("1255.13");
  });

  it("devuelve cadena vacía para entrada vacía", () => {
    expect(parsearImporte("")).toBe("");
  });
});
