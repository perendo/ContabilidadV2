/**
 * Utilidades de formato monetario en convención europea (es-ES):
 * separador de millares "." y separador decimal ",". Ej.: 1255.13 -> "1.255,13".
 */

const formateador = new Intl.NumberFormat("es-ES", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  // El locale es-ES de ICU no agrupa por defecto los números de 4 cifras
  // (1000 -> "1000"). Se fuerza el separador de millares desde 1.000.
  useGrouping: true,
});

/**
 * Formatea un importe (string decimal con punto, procedente del backend) a la
 * convención europea. Devuelve "" para valores vacíos y el valor original si no
 * es numérico.
 */
export function formatearImporte(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "";
  const numero = typeof valor === "number" ? valor : Number(valor);
  if (Number.isNaN(numero)) return String(valor);
  return formateador.format(numero);
}

/**
 * Convierte un importe tecleado en formato europeo ("1.255,13") al string
 * decimal con punto que espera el backend ("1255.13"). Acepta también el punto
 * como separador decimal cuando no hay coma ("1000.00").
 */
export function parsearImporte(texto: string): string {
  let s = texto.trim().replace(/\s/g, "").replace(/[€$]/g, "");
  if (s === "") return "";

  const signo = s.startsWith("-") ? "-" : "";
  if (signo) s = s.slice(1);

  if (s.includes(",")) {
    // La coma es el decimal: los puntos son separadores de millares.
    s = s.replace(/\./g, "").replace(",", ".");
  } else {
    // Sin coma: un punto seguido de 1-2 dígitos finales es decimal; si no, millares.
    const decimal = s.match(/^(\d+)\.(\d{1,2})$/);
    s = decimal ? `${decimal[1]}.${decimal[2]}` : s.replace(/\./g, "");
  }

  if (s.endsWith(".")) s = s.slice(0, -1);
  return signo + s;
}
