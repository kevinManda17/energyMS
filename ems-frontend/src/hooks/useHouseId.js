import { useQuery } from "@tanstack/react-query";
import { housesApi } from "../api/endpoints";
import { useUIStore } from "../store/ui";

/** Returns the selected house id, or the first available one. */
export function useHouseId() {
  const currentHouseId = useUIStore((s) => s.currentHouseId);
  const { data } = useQuery({ queryKey: ["houses"], queryFn: housesApi.list });
  const list = data?.results || data || [];
  return currentHouseId || list[0]?.id || null;
}
