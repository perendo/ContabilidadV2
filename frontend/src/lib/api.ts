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
  origen?: string | null;
  regla_id?: number | null;
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

// Facturas, Libros de IVA y Retenciones (spec 005)
export interface LineaFacturaIVAIn {
  numero_linea: number;
  descripcion: string;
  base_imponible: string;
  tipo_iva: string;
  cuota_iva?: string | null;
  tipo_re?: string | null;
  cuota_re?: string | null;
  operacion_exenta?: boolean;
  base_retencion?: string | null;
  pct_retencion?: string | null;
  cuota_retencion?: string | null;
}

export interface FacturaIn {
  origen: "venta" | "compra";
  numero: string;
  fecha: string;
  fecha_operacion?: string | null;
  tercero_cif: string;
  tercero_razon_social: string;
  solo_identificativo?: boolean;
  tipo_retencion?: "111" | "115" | null;
  notas?: string | null;
  lineas: LineaFacturaIVAIn[];
}

export interface LineaFacturaIVAOut {
  id: number;
  numero_linea: number;
  descripcion: string;
  base_imponible: string;
  tipo_iva: string;
  cuota_iva: string;
  tipo_re: string | null;
  cuota_re: string | null;
  operacion_exenta: boolean;
  base_retencion: string | null;
  pct_retencion: string | null;
  cuota_retencion: string | null;
}

export interface FacturaOut {
  id: number;
  ejercicio_id: number;
  origen: string;
  numero: string;
  fecha: string;
  fecha_operacion: string | null;
  tercero_cif: string;
  tercero_razon_social: string;
  solo_identificativo: boolean;
  tipo_retencion: string | null;
  estado: string;
  notas: string | null;
  asiento_id: number | null;
  creado_por_usuario_id: number;
  created_at: string | null;
  lineas: LineaFacturaIVAOut[];
}

export interface FacturaResumen {
  id: number;
  origen: string;
  numero: string;
  fecha: string;
  tercero_cif: string;
  tercero_razon_social: string;
  tipo_retencion: string | null;
  estado: string;
  asiento_id: number | null;
}

export type FacturasPaginado = Paginado<FacturaResumen>;

export interface LibroIVARow {
  fecha: string;
  numero: string;
  tercero_cif: string;
  tercero_razon_social: string;
  base_imponible: string;
  tipo_iva: string;
  cuota_iva: string;
  total: string;
  asiento_id: number | null;
}

export interface TotalPorTipo {
  tipo_iva: string;
  base: string;
  cuota: string;
}

export interface LibroIVAResponse {
  origen: string;
  desde: string;
  hasta: string;
  operaciones: LibroIVARow[];
  totales_por_tipo: TotalPorTipo[];
  total_base: string;
  total_cuota: string;
}

export interface ResumenRetencionItem {
  tercero_cif: string;
  tercero_razon_social: string;
  base_retencion: string;
  cuota_retencion: string;
  numero_facturas: number;
}

export interface RetencionesResponse {
  tipo: string;
  desde: string;
  hasta: string;
  por_perceptor: ResumenRetencionItem[];
  total_base: string;
  total_retencion: string;
}

// Liquidación del Impuesto sobre Sociedades (spec 005)
export interface AjusteIS {
  concepto: string;
  sentido: "aumento" | "disminucion";
  importe: string;
}

export interface LiquidacionISIn {
  resultado_contable: string;
  ajustes: AjusteIS[];
  tipo_gravamen?: string;
  retenciones_pagos_cuenta?: string;
}

export interface LiquidacionISOut {
  id: number;
  ejercicio_id: number;
  resultado_contable: string;
  ajustes: AjusteIS[];
  tipo_gravamen: string;
  retenciones_pagos_cuenta: string;
  base_imponible: string | null;
  cuota_integra: string | null;
  cuota_diferencial: string | null;
  estado: string;
  asiento_id: number | null;
  creado_por_usuario_id: number | null;
  cerrado_por_usuario_id: number | null;
  created_at: string | null;
  cerrado_at: string | null;
}

// Presentación AEAT (spec 005)
export interface CasillaPresentacion {
  casilla: number;
  label: string;
  importe: string;
}

export interface PresentacionVista {
  modelo: string;
  periodo: string;
  cerrada: boolean;
  resumen: Record<string, string | number | null>;
  casillas: CasillaPresentacion[];
  bloque_descarga: { habilitado: boolean; motivo: string | null };
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

function deleteCookie(nombre: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${nombre}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; samesite=lax`;
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

async function descargarFichero(path: string, fallbackFilename: string): Promise<void> {
  const headers: Record<string, string> = {};
  const empresaId = getEmpresaId();
  const ejercicioId = getEjercicioId();
  if (empresaId) headers["X-Empresa-Id"] = empresaId;
  if (ejercicioId) headers["X-Ejercicio-Id"] = ejercicioId;

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
  let filename = fallbackFilename;
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
}

export const api = {
  me: () => request<UsuarioPerfil>("/auth/me"),
  login: (username: string, password: string) =>
    request<{ access_token: string; expires_in: number }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      // Limpia el contexto de empresa/ejercicio para que no se filtre a otra
      // sesión en el mismo navegador (evita 403/contexto cruzado al re-loguear).
      deleteCookie("empresa_id");
      deleteCookie("ejercicio_id");
    }
  },
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
  // El backend acota `limit` a 200; para selectores que necesitan el plan completo
  // se recorren las páginas y se concatenan los items.
  todasLasCuentas: async (params: { query?: string; nivel?: number } = {}) => {
    const limit = 200;
    const items: Cuenta[] = [];
    for (let offset = 0; ; ) {
      const page = await api.cuentas({ ...params, offset, limit });
      items.push(...page.items);
      offset += page.items.length;
      if (page.items.length === 0 || offset >= page.total) break;
    }
    return items;
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
    // US4: vincula un movimiento a un asiento creado manualmente y lo marca procesado.
    marcarProcesado: (movimientoId: number, asientoId: number) =>
      request<MovimientoBanco>(`/banco/movimientos/${movimientoId}/procesado`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asiento_id: asientoId }),
      }),
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
    await descargarFichero(`/informes/${tipo}/export?${q.toString()}`, `${tipo}.${formato}`);
  },

  // Facturas, Libros de IVA y Retenciones (spec 005)
  facturas: {
    crear: (payload: FacturaIn) =>
      request<FacturaOut>("/facturas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    listar: (
      params: {
        origen?: "venta" | "compra";
        desde?: string;
        hasta?: string;
        tercero_cif?: string;
        offset?: number;
        limit?: number;
      } = {}
    ) => {
      const q = new URLSearchParams();
      if (params.origen) q.set("origen", params.origen);
      if (params.desde) q.set("desde", params.desde);
      if (params.hasta) q.set("hasta", params.hasta);
      if (params.tercero_cif) q.set("tercero_cif", params.tercero_cif);
      q.set("offset", String(params.offset ?? 0));
      q.set("limit", String(params.limit ?? 50));
      return request<FacturasPaginado>(`/facturas?${q.toString()}`);
    },
    detalle: (id: number) => request<FacturaOut>(`/facturas/${id}`),
    libro: (params: { origen: "repercutido" | "soportado"; desde: string; hasta: string }) => {
      const q = new URLSearchParams();
      q.set("origen", params.origen);
      q.set("desde", params.desde);
      q.set("hasta", params.hasta);
      return request<LibroIVAResponse>(`/facturas/libros/iva?${q.toString()}`);
    },
    exportarLibro: (params: {
      origen: "repercutido" | "soportado";
      desde: string;
      hasta: string;
    }) => {
      const q = new URLSearchParams();
      q.set("origen", params.origen);
      q.set("desde", params.desde);
      q.set("hasta", params.hasta);
      return descargarFichero(
        `/facturas/libros/iva/exportar?${q.toString()}`,
        `libro_iva_${params.origen}.csv`
      );
    },
    retenciones: (params: { tipo: "111" | "115"; desde: string; hasta: string }) => {
      const q = new URLSearchParams();
      q.set("tipo", params.tipo);
      q.set("desde", params.desde);
      q.set("hasta", params.hasta);
      return request<RetencionesResponse>(`/facturas/retenciones?${q.toString()}`);
    },
  },

  // Liquidación del Impuesto sobre Sociedades (spec 005, US5)
  impuestoSociedades: {
    obtener: () => request<LiquidacionISOut>("/is"),
    crear: (payload: LiquidacionISIn) =>
      request<LiquidacionISOut>("/is", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    actualizar: (payload: LiquidacionISIn) =>
      request<LiquidacionISOut>("/is", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    cerrar: () => request<LiquidacionISOut>("/is/cerrar", { method: "POST" }),
  },

  // Presentación AEAT (spec 005, US-PRES)
  presentaciones: {
    vista: (modelo: string, periodo: string) => {
      const q = new URLSearchParams();
      q.set("periodo", periodo);
      return request<PresentacionVista>(`/presentaciones/${modelo}?${q.toString()}`);
    },
    descargarFichero: (modelo: string, periodo: string) => {
      const q = new URLSearchParams();
      q.set("periodo", periodo);
      return descargarFichero(
        `/presentaciones/${modelo}/fichero?${q.toString()}`,
        `${modelo}_${periodo}.txt`
      );
    },
  },
};