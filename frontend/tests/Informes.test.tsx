import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import Mayor from "@/components/Mayor";
import Balance from "@/components/Balance";

vi.mock("@/lib/api", () => {
  return {
    api: {
      cuentas: vi.fn().mockResolvedValue({ items: [
        { id: 1, codigo: "570", nombre: "Caja", nivel: 3 },
        { id: 2, codigo: "410", nombre: "Proveedores", nivel: 3 },
      ]}),
      mayor: vi.fn(),
      mayorCuentas: vi.fn(),
      balance: vi.fn(),
      descargarInforme: vi.fn(),
    },
  };
});

import { api } from "@/lib/api";

describe("Mayor component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.cuentas as any).mockResolvedValue({ items: [
      { id: 1, codigo: "570", nombre: "Caja", nivel: 3 },
      { id: 2, codigo: "410", nombre: "Proveedores", nivel: 3 },
    ]});
  });

  it("renderiza selector de cuenta y filtros de fecha", () => {
    render(<Mayor />);
    expect(screen.getByLabelText("Cuenta")).toBeInTheDocument();
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();
    expect(screen.getByLabelText("Hasta")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Consultar/i })).toBeInTheDocument();
  });

  it("cambia a listado global", () => {
    render(<Mayor />);
    const tabs = screen.getByRole("tablist");
    expect(tabs).toBeInTheDocument();
  });
});

describe("Balance component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.cuentas as any).mockResolvedValue({ items: [
      { id: 1, codigo: "570", nombre: "Caja", nivel: 3 },
      { id: 2, codigo: "410", nombre: "Proveedores", nivel: 3 },
    ]});
  });

  it("renderiza filtros de fecha y botón consultar", () => {
    render(<Balance />);
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();
    expect(screen.getByLabelText("Hasta")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Consultar/i })).toBeInTheDocument();
  });
});