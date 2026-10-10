export interface UsuarioPerfil {
  id: number;
  username: string;
  email: string;
  rol: string;
  activo: boolean;
  empresas: number[];
}

export interface Empresa {
  id: number;
  cif: string;
  razon_social: string;
  nombre_comercial: string | null;
  activa: boolean;
}

export interface Ejercicio {
  id: number;
  empresa_id: number;
  anio: number;
  fecha_inicio: string;
  fecha_fin: string;
  estado: string;
}

export interface Cuenta {
  id: number;
  ejercicio_id: number;
  codigo: string;
  nombre: string;
  nivel: number;
}

export interface Paginado<T> {
  total: number;
  offset: number;
  limit: number;
  items: T[];
}

export interface ApunteIn {
  cuenta_id: number;
  debe: string;
  haber: string;
}

export interface AsientoResumen {
  id: number;
  ejercicio_id: number;
  numero: number | null;
  fecha: string;
  concepto: string;
  estado: string;
  total_debe: string;
  total_haber: string;
  delta?: string | null;
}

export interface AsientoDetalle extends Omit<AsientoResumen, "total_debe" | "total_haber" | "delta"> {
  apuntes: { cuenta_id: number; cuenta_codigo: string; debe: string; haber: string }[];
}

// Informes - Libro Mayor
export interface CuentaRef {
  codigo: string;
  nombre: string;
  nivel: number;
}

export interface MovimientoMayor {
  fecha: string;
  numero: number;
  asiento_id: number;
  concepto: string;
  debe: string;
  haber: string;
  saldo: string;
}

export interface MayorCuenta {
  cuenta: CuentaRef;
  desde: string | null;
  hasta: string | null;
  saldo_inicial: string;
  movimientos: MovimientoMayor[];
  total_debe: string;
  total_haber: string;
  saldo_final: string;
}

export interface FilaMayorCuenta {
  codigo: string;
  nombre: string;
  nivel: number;
  suma_debe: string;
  suma_haber: string;
  saldo: string;
  saldo_tipo: "deudor" | "acreedor" | "cero";
}

export interface MayorGlobal {
  ejercicio_id: number;
  desde: string | null;
  hasta: string | null;
  cuentas: FilaMayorCuenta[];
}

// Informes - Balance de Sumas y Saldos
export interface FilaBalance {
  codigo: string;
  nombre: string;
  nivel: number;
  suma_debe: string;
  suma_haber: string;
  saldo_deudor: string;
  saldo_acreedor: string;
}

export interface Balance {
  ejercicio_id: number;
  desde: string | null;
  hasta: string | null;
  filas: FilaBalance[];
  total_debe: string;
  total_haber: string;
  total_saldo_deudor: string;
  total_saldo_acreedor: string;
  cuadra: boolean;
}

// Banco - Conciliación Bancaria
export interface MovimientoBanco {
  id: number;
  ejercicio_id: number;
  fecha_operacion: string;
  fecha_valor: string;
  concepto: string;
  referencia: string | null;
  referencia_2: string | null;
  importe: string;
  saldo: string;
  divisa: string;
  codigo_banco: string | null;
  numero_documento: string | null;
  info_adicional: string | null;
  procesado: boolean;
  asiento_id: number | null;
  regla_id: number | null;
  hash_unicidad: string;
  origen_archivo: string;
}

export interface ImportResponse {
  importados: number;
  duplicados: number;
  errores: string[];
  formato_detectado: "excel" | "csv" | "csb";
}

export interface ReglaBanco {
  id: number;
  empresa_id: number;
  nombre: string;
  patron_regex: string;
  cuenta_debe: string;
  cuenta_haber: string;
  importe_fijo: string | null;
  porcentaje: string | null;
  prioridad: number;
  auto_asentar: boolean;
  activa: boolean;
}

export interface ReglaBancoIn {
  nombre: string;
  patron_regex: string;
  cuenta_debe: string;
  cuenta_haber: string;
  importe_fijo?: string | null;
  porcentaje?: string | null;
  prioridad?: number;
  auto_asentar?: boolean;
  activa?: boolean;
}

export interface MatchItem {
  movimiento_id: number;
  fecha_operacion: string;
  fecha_valor: string;
  concepto: string;
  importe: string;
  saldo: string;
  cuenta_debe: string;
  cuenta_haber: string;
  importe_calculado: string;
}

export interface SimularResponse {
  matches: MatchItem[];
}

export interface ProcesarResponse {
  creados: number;
  pendientes: number;
  fallidos: { movimiento_id: number; error: string }[];
  log_id: number;
}

export interface LogProcesamiento {
  id: number;
  ejercicio_id: number;
  usuario_id: number;
  timestamp: string;
  reglas_aplicadas_json: string;
  creados: number;
  pendientes: number;
  fallidos_json: string;
}

const CONTEXTO_KEY = "contexto-cambiado";

function getCookie(nombre: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(new RegExp("(?:^|; )" + nombre + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : undefined;
}

function setCookie(nombre: string, valor: string) {
  document.cookie = `${nombre}=${encodeURIComponent(valor)}; path=/; samesite=lax`;
}

export function getEmpresaId(): string | undefined {
  return getCookie("empresa_id");
}

export function getEjercicioId(): string | undefined {
  return getCookie("ejercicio_id");
}

export function setEmpresaId(id: string | number) {
  setCookie("empresa_id", String(id));
  window.dispatchEvent(new Event(CONTEXTO_KEY));
}

export function setEjercicioId(id: string | number) {
  setCookie("ejercicio_id", String(id));
  window.dispatchEvent(new Event(CONTEXTO_KEY));
}

export function onChangeContexto(cb: () => void): () => void {
  window.addEventListener(CONTEXTO_KEY, cb);
  return () => window.removeEventListener(CONTEXTO_KEY, cb);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  const method = (options.method || "GET").toUpperCase();
  const empresaId = getEmpresaId();
  const ejercicioId = getEjercicioId();
  if (empresaId) headers["X-Empresa-Id"] = empresaId;
  if (ejercicioId) headers["X-Ejercicio-Id"] = ejercicioId;

  // Anti-CSRF (SEC-02): cabecera para peticiones mutacionales
  if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
    headers["X-Requested-With"] = "XMLHttpRequest";
  }

  const res = await fetch(`/api/v1${path}`, { ...options, headers });
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `Error ${res.status}`;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const api = {
  me: () => request<UsuarioPerfil>("/auth/me"),
  login: (username: string, password: string) =>
    request<{ access_token: string; expires_in: number }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  empresas: () => request<Empresa[]>("/empresas"),
  crearEmpresa: (payload: {
    cif: string;
    razon_social: string;
    nombre_comercial?: string | null;
  }) =>
    request<Empresa>("/empresas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  ejercicios: () => request<Ejercicio[]>("/ejercicios"),
  crearEjercicio: (payload: { anio: number; fecha_inicio: string; fecha_fin: string }) =>
    request<Ejercicio>("/ejercicios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  cuentas: (params: { query?: string; nivel?: number; offset?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.query) q.set("query", params.query);
    if (params.nivel) q.set("nivel", String(params.nivel));
    q.set("offset", String(params.offset ?? 0));
    q.set("limit", String(params.limit ?? 200));
    return request<Paginado<Cuenta>>(`/cuentas?${q.toString()}`);
  },
  crearCuenta: (payload: { codigo: string; nombre: string; nivel: number }) =>
    request<Cuenta>("/cuentas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  guardarAsiento: (payload: {
    fecha: string;
    concepto: string;
    apuntes: ApunteIn[];
  }) =>
    request<AsientoDetalle>("/asientos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  editarAsiento: (
    id: number,
    payload: { fecha: string; concepto: string; apuntes: ApunteIn[] }
  ) =>
    request<AsientoDetalle>(`/asientos/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  asentarAsiento: (id: number) =>
    request<AsientoDetalle>(`/asientos/${id}/asentar`, { method: "POST" }),
  diario: (params: {
    since?: string;
    until?: string;
    offset?: number;
    limit?: number;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.since) q.set("since", params.since);
    if (params.until) q.set("until", params.until);
    q.set("offset", String(params.offset ?? 0));
    q.set("limit", String(params.limit ?? 50));
    return request<Paginado<AsientoResumen>>(`/asientos?${q.toString()}`);
  },
  borradores: (params: { offset?: number; limit?: number } = {}) => {
    const q = new URLSearchParams();
    q.set("offset", String(params.offset ?? 0));
    q.set("limit", String(params.limit ?? 50));
    return request<Paginado<AsientoResumen>>(`/asientos/borradores?${q.toString()}`);
  },
  asientoDetalle: (id: number) => request<AsientoDetalle>(`/asientos/${id}`),

  // Banco - Conciliación Bancaria
  banco: {
    importar: (file: File, ignorarDuplicados = false) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("ignorar_duplicados", String(ignorarDuplicados));
      return request<ImportResponse>("/banco/importar", {
        method: "POST",
        body: formData,
      });
    },
    pendientes: (params: { desde?: string; hasta?: string; codigo_banco?: string; offset?: number; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (params.desde) q.set("desde", params.desde);
      if (params.hasta) q.set("hasta", params.hasta);
      if (params.codigo_banco) q.set("codigo_banco", params.codigo_banco);
      q.set("offset", String(params.offset ?? 0));
      q.set("limit", String(params.limit ?? 50));
      return request<MovimientoBanco[]>(`/banco/pendientes?${q.toString()}`);
    },
    reglas: () => request<ReglaBanco[]>("/banco/reglas"),
    crearRegla: (payload: ReglaBancoIn) =>
      request<ReglaBanco>("/banco/reglas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    actualizarRegla: (id: number, payload: ReglaBancoIn) =>
      request<ReglaBanco>(`/banco/reglas/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    borrarRegla: (id: number) =>
      request<void>(`/banco/reglas/${id}`, { method: "DELETE" }),
    simularRegla: (id: number, params: { desde?: string; hasta?: string } = {}) => {
      const q = new URLSearchParams();
      if (params.desde) q.set("desde", params.desde);
      if (params.hasta) q.set("hasta", params.hasta);
      return request<{ matches: MatchItem[] }>(`/banco/reglas/${id}/simular?${q.toString()}`);
    },
    procesar: (params: { desde?: string; hasta?: string } = {}) => {
      const q = new URLSearchParams();
      if (params.desde) q.set("desde", params.desde);
      if (params.hasta) q.set("hasta", params.hasta);
      return request<ProcesarResponse>(`/banco/procesar?${q.toString()}`, { method: "POST" });
    },
    logs: (params: { desde?: string; hasta?: string; offset?: number; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (params.desde) q.set("desde", params.desde);
      if (params.hasta) q.set("hasta", params.hasta);
      q.set("offset", String(params.offset ?? 0));
      q.set("limit", String(params.limit ?? 50));
      return request<LogProcesamiento[]>(`/banco/logs?${q.toString()}`);
    },
  },

  // Informes - Libro Mayor
  mayor: (cuenta: string, params: { desde?: string; hasta?: string } = {}) => {
    const q = new URLSearchParams();
    q.set("cuenta", cuenta);
    if (params.desde) q.set("desde", params.desde);
    if (params.hasta) q.set("hasta", params.hasta);
    return request<MayorCuenta>(`/informes/mayor?${q.toString()}`);
  },
  mayorCuentas: (params: { desde?: string; hasta?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.desde) q.set("desde", params.desde);
    if (params.hasta) q.set("hasta", params.hasta);
    return request<MayorGlobal>(`/informes/mayor/cuentas?${q.toString()}`);
  },

  // Informes - Balance de Sumas y Saldos
  balance: (params: { desde?: string; hasta?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.desde) q.set("desde", params.desde);
    if (params.hasta) q.set("hasta", params.hasta);
    return request<Balance>(`/informes/balance?${q.toString()}`);
  },

  // Exportación
  descargarInforme: async (
    tipo: "mayor" | "balance",
    formato: "csv" | "pdf",
    params: { cuenta?: string; desde?: string; hasta?: string } = {}
  ) => {
    const q = new URLSearchParams();
    q.set("formato", formato);
    if (tipo === "mayor" && params.cuenta) q.set("cuenta", params.cuenta);
    if (params.desde) q.set("desde", params.desde);
    if (params.hasta) q.set("hasta", params.hasta);

    const headers: Record<string, string> = {};
    const empresaId = getEmpresaId();
    const ejercicioId = getEjercicioId();
    if (empresaId) headers["X-Empresa-Id"] = empresaId;
    if (ejercicioId) headers["X-Ejercicio-Id"] = ejercicioId;

    const path = `/informes/${tipo}/export?${q.toString()}`;
    const res = await fetch(`/api/v1${path}`, { headers, credentials: "include" });
    if (!res.ok) {
      const text = await res.text();
      let detail = `Error ${res.status}`;
      try {
        const data = JSON.parse(text);
        if (data.detail) detail = data.detail;
      } catch {
        detail = text || detail;
      }
      throw new ApiError(res.status, detail);
    }

    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition");
    let filename = `${tipo}.${formato}`;
    if (disposition) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match) filename = match[1];
    }

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};