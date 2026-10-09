import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import FormAsiento, { calcularDelta } from "@/components/FormAsiento";

const cuentas = [
  { id: 7, codigo: "57200001", nombre: "Bancos c/c" },
  { id: 12, codigo: "41000000", nombre: "Proveedores" },
];

function setup() {
  const onGuardarBorrador = vi.fn().mockResolvedValue(undefined);
  const onAsentar = vi.fn().mockResolvedValue(undefined);
  render(
    <FormAsiento
      cuentas={cuentas}
      ejercicioAbierto
      onGuardarBorrador={onGuardarBorrador}
      onAsentar={onAsentar}
    />
  );
  return { onGuardarBorrador, onAsentar };
}

async function rellenarLinea(i: number, cuenta: number, debe: string, haber: string) {
  const user = userEvent.setup();
  const fila = screen.getByTestId(`fila-${i}`);
  const selects = fila.querySelectorAll("select");
  const inputs = fila.querySelectorAll('input[type="number"]');
  await user.selectOptions(selects[0], String(cuenta));
  await user.clear(inputs[0]);
  if (debe) {
    await user.type(inputs[0], debe);
  }
  await user.clear(inputs[1]);
  if (haber) {
    await user.type(inputs[1], haber);
  }
}

describe("FormAsiento", () => {
  it("calcula Δ correctamente sin errores de coma flotante IEEE 754 (T033)", () => {
    expect(
      calcularDelta([
        { id: 1, cuentaId: "7", debe: "0.10", haber: "" },
        { id: 2, cuentaId: "7", debe: "0.20", haber: "" },
        { id: 3, cuentaId: "12", debe: "", haber: "0.30" },
      ])
    ).toBe("0.00");
  });

  it("calcula Δ en tiempo real sobre N líneas descuadradas", () => {
    expect(
      calcularDelta([
        { id: 1, cuentaId: "7", debe: "1000.00", haber: "" },
        { id: 2, cuentaId: "12", debe: "", haber: "900.00" },
      ])
    ).toBe("100.00");
    expect(
      calcularDelta([
        { id: 1, cuentaId: "7", debe: "300", haber: "" },
        { id: 2, cuentaId: "12", debe: "400", haber: "" },
        { id: 3, cuentaId: "7", debe: "", haber: "700" },
      ])
    ).toBe("0.00");
  });

  it("bloquea asentar si Δ≠0 pero permite guardar borrador", async () => {
    const user = userEvent.setup();
    setup();
    await rellenarLinea(1, 7, "1000.00", "");
    await rellenarLinea(2, 12, "", "900.00");
    await user.type(screen.getByTestId("concepto"), "Pago proveedor");

    expect(screen.getByTestId("asentar")).toBeDisabled();
    expect(screen.getByTestId("guardar-borrador")).toBeEnabled();
  });

  it("habilita asentar cuando el conjunto cuadra (Δ=0)", async () => {
    const user = userEvent.setup();
    setup();
    await rellenarLinea(1, 7, "1000.00", "");
    await rellenarLinea(2, 12, "", "1000.00");
    await user.type(screen.getByTestId("concepto"), "Pago proveedor");

    expect(screen.getByTestId("asentar")).toBeEnabled();
  });
});