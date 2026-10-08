import { useCallback, useEffect, useState } from "react";

import { ApiError, onChangeContexto } from "@/lib/api";

export function useCargar<T>(cargar: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const recargar = useCallback(() => {
    setLoading(true);
    setError(null);
    cargar()
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Error de red"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    recargar();
    const off = onChangeContexto(recargar);
    return off;
  }, [recargar]);

  return { data, loading, error, setData, recargar };
}