import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  Bell,
  Check,
  ChevronDown,
  Home,
  LogOut,
  Menu,
  Moon,
  Search,
  Sun,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useUIStore } from "../store/ui";
import { useAuthStore } from "../store/auth";
import { housesApi, alertsApi } from "../api/endpoints";

export default function Topbar() {
  const navigate = useNavigate();
  const { toggleSidebar, theme, toggleTheme, currentHouseId, setHouse } =
    useUIStore();
  const { user, logout } = useAuthStore();
  const [housePickerOpen, setHousePickerOpen] = useState(false);
  const [search, setSearch] = useState("");

  const { data: houses } = useQuery({
    queryKey: ["houses"],
    queryFn: housesApi.list,
  });
  const { data: unread } = useQuery({
    queryKey: ["alerts", "unread"],
    queryFn: alertsApi.unread,
    refetchInterval: 30000,
  });

  const houseList = houses?.results || houses || [];
  const selectedHouse = houseList.find((house) => house.id === currentHouseId);
  const unreadCount = unread?.count ?? unread?.length ?? 0;
  const filteredHouses = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return houseList;
    return houseList.filter((house) =>
      [house.name, house.location, house.status]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(term)
    );
  }, [houseList, search]);

  useEffect(() => {
    if (!housePickerOpen) return undefined;
    function closeOnEscape(event) {
      if (event.key === "Escape") setHousePickerOpen(false);
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [housePickerOpen]);

  function chooseHouse(id) {
    setHouse(id || null);
    setHousePickerOpen(false);
    setSearch("");
  }

  function logoutAndLeave() {
    logout();
    navigate("/login");
  }

  return (
    <header className="sticky top-0 z-20 flex min-w-0 items-center gap-2 border-b border-slate-200 bg-white/95 px-3 py-3 backdrop-blur dark:border-white/5 dark:bg-[#0B1220]/95 sm:gap-3 sm:px-4">
      <button
        className="btn-ghost shrink-0 p-2 lg:hidden"
        onClick={toggleSidebar}
        aria-label="Ouvrir le menu"
      >
        <Menu size={22} />
      </button>

      <div className="relative min-w-0 flex-1 sm:flex-none">
        <button
          type="button"
          onClick={() => setHousePickerOpen(true)}
          className="flex h-11 w-full min-w-0 items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 text-left text-sm font-semibold text-navy shadow-sm transition hover:border-electric/60 dark:border-white/10 dark:bg-[#071923] dark:text-white sm:w-80"
          aria-haspopup="dialog"
          aria-expanded={housePickerOpen}
        >
          <span className="min-w-0 truncate">
            {selectedHouse ? selectedHouse.name : "Tous les micro-reseaux"}
          </span>
          <ChevronDown size={16} className="shrink-0 text-slate-400" />
        </button>
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
        <button className="btn-ghost p-2" onClick={toggleTheme} title="Theme">
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        <button
          className="relative btn-ghost p-2"
          onClick={() => navigate("/alerts")}
          title="Alertes"
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-danger text-[10px] font-bold text-white">
              {unreadCount}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => navigate("/settings?tab=profile")}
          className="flex min-w-0 items-center gap-2 rounded-xl px-1.5 py-1.5 text-left transition hover:bg-slate-100 dark:hover:bg-white/5 sm:px-2"
          title="Informations utilisateur"
        >
          <div className="grid h-9 w-9 place-items-center rounded-full bg-electric text-sm font-bold text-white">
            {(user?.username || "U").slice(0, 2).toUpperCase()}
          </div>
          <div className="hidden text-sm md:block">
            <div className="font-semibold leading-tight">{user?.username}</div>
            <div className="text-xs text-slate-400">
              {user?.role === "ADMIN" ? "Administrateur" : "Utilisateur"}
            </div>
          </div>
        </button>

        <button
          className="btn-ghost p-2"
          onClick={logoutAndLeave}
          title="Deconnexion"
        >
          <LogOut size={18} />
        </button>
      </div>

      {housePickerOpen &&
        createPortal(
          <HousePickerDialog
            filteredHouses={filteredHouses}
            houseList={houseList}
            currentHouseId={currentHouseId}
            selectedHouse={selectedHouse}
            search={search}
            setSearch={setSearch}
            onClose={() => setHousePickerOpen(false)}
            onChoose={chooseHouse}
          />,
          document.body
        )}
    </header>
  );
}

function HousePickerDialog({
  filteredHouses,
  houseList,
  currentHouseId,
  selectedHouse,
  search,
  setSearch,
  onClose,
  onChoose,
}) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-3 sm:p-6">
      <button
        className="absolute inset-0 cursor-default bg-slate-950/20 backdrop-blur-[1px]"
        onClick={onClose}
        aria-label="Fermer la selection"
      />
      <section
        className="relative z-10 max-h-[82vh] w-full max-w-[420px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-white/10 dark:bg-[#0B1220]"
        role="dialog"
        aria-modal="true"
        aria-label="Selection du micro-reseau"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 p-4 dark:border-white/10">
          <div className="min-w-0">
            <h2 className="font-semibold text-navy dark:text-white">
              Selection du micro-reseau
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {selectedHouse
                ? `Actuel : ${selectedHouse.name}`
                : `${houseList.length} micro-reseau(x) disponible(s)`}
            </p>
          </div>
          <button className="btn-ghost p-2" onClick={onClose} aria-label="Fermer">
            <X size={17} />
          </button>
        </div>

        <div className="p-4">
          <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm dark:border-white/10 dark:bg-white/5">
            <Search size={16} className="text-slate-400" />
            <input
              className="min-w-0 flex-1 bg-transparent outline-none"
              placeholder="Rechercher une residence"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              autoFocus
            />
          </label>
        </div>

        <div className="max-h-[50vh] overflow-y-auto px-2 pb-3">
          <HouseOption
            active={!currentHouseId}
            title="Tous les micro-reseaux"
            subtitle="Vue globale"
            icon={Home}
            onClick={() => onChoose(null)}
          />
          {filteredHouses.map((house) => (
            <HouseOption
              key={house.id}
              active={house.id === currentHouseId}
              title={house.name}
              subtitle={house.location || "Micro-reseau"}
              status={house.status}
              onClick={() => onChoose(house.id)}
            />
          ))}
          {filteredHouses.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-slate-400">
              Aucun micro-reseau trouve.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function HouseOption({ active, title, subtitle, status, icon: Icon = Home, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition ${
        active
          ? "bg-blue-50 text-electric dark:bg-blue-500/10"
          : "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-white/5"
      }`}
    >
      <span
        className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${
          active
            ? "bg-electric text-white"
            : "bg-slate-100 text-slate-500 dark:bg-white/10"
        }`}
      >
        <Icon size={17} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold">{title}</span>
        <span className="mt-0.5 block truncate text-xs text-slate-400">
          {subtitle}
          {status ? ` - ${status.toLowerCase()}` : ""}
        </span>
      </span>
      {active && <Check size={18} className="shrink-0" />}
    </button>
  );
}
