import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FormFactura from "@/components/FormFactura";
import LiquidacionIS from "@/components/LiquidacionIS";
import PresentacionAEAT from "@/components/PresentacionAEAT";

vi.mock("@/lib/api", () => {
  return {
    ApiError: class ApiError extends Error {
      status: number;
      constructor(status: number, message: string) {
        super(message);
        this.status = status;
      }
    },
    onChangeContexto: vi.fn(() => () => {}),
    api: {
      presentaciones: {
        vista: vi.fn(),
        descargarFichero: vi.fn(),
      },
      impuestoSociedades: {
        obtener: vi.fn(),
        crear: vi.fn(),
        actualizar: vi.fn(),
        cerrar: vi.fn(),
      },
      facturas: {
        crear: vi.fn(),
      },
    },
  };
});

import { api } from "@/lib/api";

describe("FormFactura", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza y bloquea el registro si el CIF no tiene 9 caracteres", async () => {
    const user = userEvent.setup();
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    render(<FormFactura ejercicioAbierto onGuardar={onGuardar} />);

    const boton = screen.getByTestId("guardar-factura");
    expect(boton).toBeDisabled();

    await user.type(screen.getByLabelText("Número"), "FV-001");
    await user.type(screen.getByLabelText("CIF/NIF tercero"), "1234");
    await user.type(screen.getByLabelText("Razón social"), "Cliente SL");
    await user.type(screen.getByLabelText("descripcion-1"), "Servicio profesional");
    await user.type(screen.getByLabelText("base-1"), "1000");

    // CIF inválido (no 9 caracteres): sigue bloqueado
    expect(boton).toBeDisabled();

    await user.clear(screen.getByLabelText("CIF/NIF tercero"));
    await user.type(screen.getByLabelText("CIF/NIF tercero"), "B12345674");
    expect(boton).toBeEnabled();

    await user.click(boton);
    await waitFor(() => expect(onGuardar).toHaveBeenCalledTimes(1));
    const payload = onGuardar.mock.calls[0][0];
    expect(payload.origen).toBe("venta");
    expect(payload.tercero_cif).toBe("B12345674");
    expect(payload.lineas[0].base_imponible).toBe("1000");
  });

  it("muestra el error de duplicado devuelto por el backend", async () => {
    const user = userEvent.setup();
    const onGuardar = vi
      .fn()
      .mockRejectedValue(new Error("Factura duplicada (CIF + número + ejercicio)"));
    render(<FormFactura ejercicioAbierto onGuardar={onGuardar} />);

    await user.type(screen.getByLabelText("Número"), "FV-001");
    await user.type(screen.getByLabelText("CIF/NIF tercero"), "B12345674");
    await user.type(screen.getByLabelText("Razón social"), "Cliente SL");
    await user.type(screen.getByLabelText("descripcion-1"), "Servicio");
    await user.type(screen.getByLabelText("base-1"), "100");

    await user.click(screen.getByTestId("guardar-factura"));
    expect(await screen.findByTestId("error")).toHaveTextContent(/duplicada/i);
  });
});

describe("PresentacionAEAT", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.presentaciones.vista as any).mockResolvedValue({
      modelo: "200",
      periodo: "2026",
      cerrada: false,
      resumen: {
        resultado_contable: "100000.00",
        base_imponible: "97000.00",
        cuota_integra: "24250.00",
        cuota_diferencial: "20250.00",
      },
      casillas: [
        { casilla: 300, label: "Base imponible", importe: "97000.00" },
        { casilla: 500, label: "Cuota íntegra", importe: "24250.00" },
      ],
      bloque_descarga: {
        habilitado: false,
        motivo: "La liquidación del IS debe estar cerrada para descargar el 200",
      },
    });
  });

  it("muestra el resumen y deshabilita la descarga en borrador", async () => {
    render(<PresentacionAEAT />);

    await screen.findByTestId("resumen-presentacion");
    expect(screen.getAllByText("Base imponible").length).toBeGreaterThan(0);
    expect(screen.getAllByText("97.000,00").length).toBeGreaterThan(0);

    const boton = screen.getByTestId("descargar-fichero");
    expect(boton).toBeDisabled();
    expect(
      screen.getByText(/debe estar cerrada para descargar el 200/i)
    ).toBeInTheDocument();
  });

  it("habilita la descarga cuando el periodo está cerrado", async () => {
    const user = userEvent.setup();
    (api.presentaciones.vista as any).mockResolvedValue({
      modelo: "303",
      periodo: "2026T1",
      cerrada: true,
      resumen: { resultante: "260.00" },
      casillas: [{ casilla: 46, label: "Resultado de la liquidación", importe: "260.00" }],
      bloque_descarga: { habilitado: true, motivo: null },
    });
    (api.presentaciones.descargarFichero as any).mockResolvedValue(undefined);

    render(<PresentacionAEAT />);

    const boton = await screen.findByTestId("descargar-fichero");
    await waitFor(() => expect(boton).toBeEnabled());
    await user.click(boton);
    await waitFor(() =>
      expect(api.presentaciones.descargarFichero).toHaveBeenCalledWith("303", expect.any(String))
    );
  });
});

describe("LiquidacionIS", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("edita una liquidación en borrador y guarda con PUT", async () => {
    const liq = {
      id: 1,
      ejercicio_id: 1,
      resultado_contable: "100000.00",
      ajustes: [{ concepto: "Multas", sentido: "aumento", importe: "5000.00" }],
      tipo_gravamen: "25.00",
      retenciones_pagos_cuenta: "4000.00",
      base_imponible: "97000.00",
      cuota_integra: "24250.00",
      cuota_diferencial: "20250.00",
      estado: "borrador",
      asiento_id: null,
      creado_por_usuario_id: 1,
      cerrado_por_usuario_id: null,
      created_at: null,
      cerrado_at: null,
    };
    (api.impuestoSociedades.obtener as any).mockResolvedValue(liq);
    (api.impuestoSociedades.actualizar as any).mockResolvedValue({
      ...liq,
      resultado_contable: "105000.00",
      base_imponible: "102000.00",
    });

    const user = userEvent.setup();
    render(<LiquidacionIS />);

    await screen.findByTestId("liq-existente");
    await user.click(screen.getByTestId("editar-liq"));
    expect(screen.getByTestId("form-liq-edit")).toBeInTheDocument();

    const campo = screen.getByTestId("resultado");
    await user.clear(campo);
    await user.type(campo, "105000");
    await user.click(screen.getByTestId("guardar-liq"));

    await waitFor(() => expect(api.impuestoSociedades.actualizar).toHaveBeenCalledTimes(1));
    expect((api.impuestoSociedades.actualizar as any).mock.calls[0][0].resultado_contable).toBe(
      "105000"
    );
    // Vuelve a la vista de solo lectura con el nuevo importe
    await screen.findByTestId("liq-existente");
    expect(screen.getByTestId("base-imponible")).toHaveTextContent("102.000,00");
  });
});
