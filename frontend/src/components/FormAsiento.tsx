import { useMemo, useRef, useState } from "react";

export interface FilaApunte {
  id: number;
  cuentaId: string;
  debe: string;
  haber: string;
}

export interface CuentaOpt {
  id: number;
  codigo: string;
  nombre: string;
}

/** Δ (debe − haber) en Decimal (string) sobre N líneas. */
export function calcularDelta(apuntes: FilaApunte[]): string {
  const suma = apuntes.reduce(
    (acc, f) => {
      const debe = Number(f.debe || "0") || 0;
      const haber = Number(f.haber || "0") || 0;
      return { debe: acc.debe + debe, haber: acc.haber + haber };
    },
    { debe: 0, haber: 0 }
  );
  return (suma.debe - suma.haber).toFixed(2);
}

export function filaEstaCuadrada(f: FilaApunte): boolean {
  const debe = Number(f.debe || "0") || 0;
  const haber = Number(f.haber || "0") || 0;
  return (debe > 0) !== (haber > 0);
}

interface Props {
  cuentas: CuentaOpt[];
  ejercicioAbierto: boolean;
  inicial?: {
    id: number;
    fecha: string;
    concepto: string;
    apuntes: { cuenta_id: number; debe: string; haber: string }[];
  } | null;
  onGuardarBorrador: (payload: {
    fecha: string;
    concepto: string;
    apuntes: { cuenta_id: number; debe: string; haber: string }[];
  }) => Promise<void>;
  onAsentar?: (payload: {
    fecha: string;
    concepto: string;
    apuntes: { cuenta_id: number; debe: string; haber: string }[];
  }) => Promise<void>;
}

export default function FormAsiento({
  cuentas,
  ejercicioAbierto,
  inicial,
  onGuardarBorrador,
  onAsentar,
}: Props) {
  const [fecha, setFecha] = useState(() => inicial?.fecha ?? new Date().toISOString().slice(0, 10));
  const [concepto, setConcepto] = useState(() => inicial?.concepto ?? "");
  const [filas, setFilas] = useState<FilaApunte[]>(() =>
    inicial
      ? inicial.apuntes.map((a, i) => ({
          id: i + 1,
          cuentaId: String(a.cuenta_id),
          debe: a.debe === "0.00" ? "" : a.debe,
          haber: a.haber === "0.00" ? "" : a.haber,
        }))
      : [
          { id: 1, cuentaId: "", debe: "", haber: "" },
          { id: 2, cuentaId: "", debe: "", haber: "" },
        ]
  );
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const nextIdRef = useRef((inicial?.apuntes.length ?? 2) + 1);

  const delta = useMemo(() => calcularDelta(filas), [filas]);
  const cuadra = delta === "0.00" && filas.every((f) => f.cuentaId !== "" && filaEstaCuadrada(f));

  function actualizar(id: number, campo: "cuentaId" | "debe" | "haber", valor: string) {
    setFilas((prev) => prev.map((f) => (f.id === id ? { ...f, [campo]: valor } : f)));
  }

  function anadirFila() {
    setFilas((prev) => [...prev, { id: nextIdRef.current++, cuentaId: "", debe: "", haber: "" }]);
  }

  function quitarFila(id: number) {
    if (filas.length > 2) {
      setFilas((prev) => prev.filter((f) => f.id !== id));
    }
  }

  function construirPayload() {
    return {
      fecha,
      concepto,
      apuntes: filas.map((f) => ({
        cuenta_id: Number(f.cuentaId),
        debe: f.debe || "0.00",
        haber: f.haber || "0.00",
      })),
    };
  }

  async function guardarBorrador() {
    setGuardando(true);
    setError(null);
    setMsg(null);
    try {
      await onGuardarBorrador(construirPayload());
      setMsg("Borrador guardado");
      setFilas([
        { id: nextIdRef.current++, cuentaId: "", debe: "", haber: "" },
        { id: nextIdRef.current++, cuentaId: "", debe: "", haber: "" },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setGuardando(false);
    }
  }

  async function asentar() {
    if (!onAsentar) return;
    setGuardando(true);
    setError(null);
    setMsg(null);
    try {
      await onAsentar(construirPayload());
      setMsg("Asiento asentado");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al asentar");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div data-testid="form-asiento">
      <h2>Nuevo asiento</h2>
      <label>
        Fecha
        <input type="date" data-testid="fecha" value={fecha} onChange={(e) => setFecha(e.target.value)} />
      </label>
      <label>
        Concepto
        <input
          data-testid="concepto"
          value={concepto}
          onChange={(e) => setConcepto(e.target.value)}
        />
      </label>

      {filas.map((fila) => (
        <div key={fila.id} data-testid={`fila-${fila.id}`}>
          <select
            aria-label="cuenta"
            value={fila.cuentaId}
            onChange={(e) => actualizar(fila.id, "cuentaId", e.target.value)}
          >
            <option value="">Seleccionar cuenta…</option>
            {cuentas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo} — {c.nombre}
              </option>
            ))}
          </select>
          <input
            aria-label="debe"
            type="number"
            step="0.01"
            value={fila.debe}
            onChange={(e) => actualizar(fila.id, "debe", e.target.value)}
          />
          <input
            aria-label="haber"
            type="number"
            step="0.01"
            value={fila.haber}
            onChange={(e) => actualizar(fila.id, "haber", e.target.value)}
          />
          <button disabled={filas.length <= 2} onClick={() => quitarFila(fila.id)}>
            Quitar
          </button>
        </div>
      ))}
      <button onClick={anadirFila}>Añadir línea</button>

      <p data-testid="delta">
        Δ = <strong>{delta}</strong>
      </p>

      <button
        data-testid="guardar-borrador"
        disabled={guardando || concepto.trim() === ""}
        onClick={guardarBorrador}
      >
        Guardar borrador
      </button>
      <button
        data-testid="asentar"
        disabled={guardando || !cuadra || !ejercicioAbierto || !onAsentar}
        onClick={asentar}
      >
        Asentar
      </button>

      {msg && <p data-testid="mensaje">{msg}</p>}
      {error && <p data-testid="error">{error}</p>}
    </div>
  );
}