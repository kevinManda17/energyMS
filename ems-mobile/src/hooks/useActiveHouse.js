import { useCallback, useEffect, useState } from "react";
import { housesApi } from "../api/endpoints";
import { storage } from "../storage";

export function useActiveHouse() {
  const [houses, setHouses] = useState([]);
  const [houseId, setHouseIdState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await housesApi.list();
      const list = res.data?.results || res.data || [];
      const stored = await storage.getHouseId();
      const active = stored && list.some((h) => h.id === stored) ? stored : list[0]?.id || null;
      setHouses(list);
      setHouseIdState(active);
      setOffline(!!res.fromCache);
      if (active) await storage.setHouseId(active);
    } catch {
      setHouses([]);
      setHouseIdState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  async function setHouseId(id) {
    setHouseIdState(id);
    await storage.setHouseId(id);
  }

  return {
    houses,
    houseId,
    activeHouse: houses.find((h) => h.id === houseId) || null,
    loading,
    offline,
    reload: load,
    setHouseId,
  };
}
