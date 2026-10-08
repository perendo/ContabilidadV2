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
  const empresaId = getEmpresaId();
  const ejercicioId = getEjercicioId();
  if (empresaId) headers["X-Empresa-Id"] = empresaId;
  if (ejercicioId) headers["X-Ejercicio-Id"] = ejercicioId;

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
};