import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BancoImportar from "@/components/BancoImportar";
import BancoPendientes from "@/components/BancoPendientes";
import BancoReglas from "@/components/BancoReglas";

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
      banco: {
        importar: vi.fn(),
        reglas: vi.fn(),
        crearRegla: vi.fn(),
        actualizarRegla: vi.fn(),
        borrarRegla: vi.fn(),
        simularRegla: vi.fn(),
        pendientes: vi.fn(),
        procesar: vi.fn(),
        marcarProcesado: vi.fn(),
        logs: vi.fn(),
      },
      todasLasCuentas: vi.fn(),
      guardarAsiento: vi.fn(),
      asentarAsiento: vi.fn(),
    },
  };
});

import { api } from "@/lib/api";

const CUENTAS = [
  { id: 1, ejercicio_id: 1, codigo: "430", nombre: "Clientes", nivel: 3 },
  { id: 2, ejercicio_id: 1, codigo: "572", nombre: "Bancos c/c", nivel: 3 },
];

const REGLA = {
  id: 1,
  empresa_id: 1,
  nombre: "UNION FENOSA",
  patron_regex: "UNION",
  cuenta_debe: "430",
  cuenta_haber: "572",
  importe_fijo: null,
  porcentaje: null,
  prioridad: 10,
  auto_asentar: false,
  activa: true,
};

describe("BancoImportar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("muestra la zona de drop y hace preview de un CSV antes de importar", async () => {
    const user = userEvent.setup();
    render(<BancoImportar />);

    expect(screen.getByText("Importar extracto bancario")).toBeInTheDocument();
    (api.banco.importar as any).mockResolvedValue({
      importados: 2,
      duplicados: 0,
      errores: [],
      formato_detectado: "csv",
    });

    const contenido = [
      "Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código",
      "01/02/2026;05/02/2026;Recibo nomina energia;1.000,50;5.000,50;572",
      "02/02/2026;06/02/2026;Pago proveedor;200,25;4.800,25;572",
    ].join("\n");
    const archivo = new File([contenido], "extracto.csv", { type: "text/csv" });

    await user.upload(screen.getByLabelText("Seleccionar archivo"), archivo);
    await screen.findByText("Recibo nomina energia");

    await user.click(screen.getByRole("button", { name: "Importar" }));
    expect(api.banco.importar).toHaveBeenCalledWith(archivo, false);
    await screen.findByText(/2 movimientos importados/);
  });
});

describe("BancoReglas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.banco.reglas as any).mockResolvedValue([REGLA]);
    (api.todasLasCuentas as any).mockResolvedValue(CUENTAS);
  });

  it("renderiza la tabla con las reglas de la empresa", async () => {
    render(<BancoReglas />);
    await screen.findByText("UNION FENOSA");
    expect(screen.getByText(/430 · Clientes/)).toBeInTheDocument();
    expect(screen.getByText(/572 · Bancos c\/c/)).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("crea una regla desde el modal", async () => {
    const user = userEvent.setup();
    (api.banco.crearRegla as any).mockResolvedValue({ ...REGLA, id: 2 });

    render(<BancoReglas />);
    await screen.findByText("UNION FENOSA");

    await user.click(screen.getByRole("button", { name: "Crear regla" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Nombre"), "IBERDROLA");
    await user.type(within(dialog).getByLabelText("Patrón regex"), "IBERDROLA");
    await user.selectOptions(within(dialog).getByLabelText("Cuenta debe"), "430");
    await user.selectOptions(within(dialog).getByLabelText("Cuenta haber"), "572");
    await user.type(within(dialog).getByLabelText("Prioridad"), "20");

    await user.click(within(dialog).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.banco.crearRegla).toHaveBeenCalled());
    const payload = (api.banco.crearRegla as any).mock.calls[0][0];
    expect(payload.nombre).toBe("IBERDROLA");
    expect(payload.cuenta_debe).toBe("430");
    expect(payload.cuenta_haber).toBe("572");
  });

  it("simula una regla y muestra los matches", async () => {
    const user = userEvent.setup();
    (api.banco.simularRegla as any).mockResolvedValue({
      matches: [
        {
          movimiento_id: 5,
          fecha_operacion: "2026-02-01",
          fecha_valor: "2026-02-05",
          concepto: "Recibo UNION FENOSA",
          importe: "125.00",
          saldo: "500.00",
          cuenta_debe: "430",
          cuenta_haber: "572",
          importe_calculado: "125.00",
        },
      ],
    });

    render(<BancoReglas />);
    await screen.findByText("UNION FENOSA");

    await user.click(screen.getByRole("button", { name: "Simular" }));
    await screen.findByText("Recibo UNION FENOSA");
    expect(api.banco.simularRegla).toHaveBeenCalledWith(1);
  });
});

describe("BancoPendientes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.banco.pendientes as any).mockResolvedValue([
      {
        id: 1,
        ejercicio_id: 1,
        fecha_operacion: "2026-02-01",
        fecha_valor: "2026-02-05",
        concepto: "Recibo nomina",
        referencia: null,
        referencia_2: null,
        importe: "-500.00",
        saldo: "2000.00",
        divisa: "EUR",
        codigo_banco: "572",
        numero_documento: null,
        info_adicional: null,
        procesado: false,
        asiento_id: null,
        regla_id: null,
        hash_unicidad: "abc",
        origen_archivo: "csv",
      },
    ]);
    (api.todasLasCuentas as any).mockResolvedValue(CUENTAS);
  });

  it("lista los pendientes y procesa automáticamente", async () => {
    const user = userEvent.setup();
    (api.banco.procesar as any).mockResolvedValue({
      creados: 0,
      pendientes: 1,
      fallidos: [],
      log_id: 7,
    });

    render(<BancoPendientes />);
    await screen.findByText("Recibo nomina");

    await user.click(screen.getByRole("button", { name: "Procesar automático" }));
    await waitFor(() => expect(api.banco.procesar).toHaveBeenCalled());
    await screen.findByText(/asientos creados · 1 pendientes/);
  });
});