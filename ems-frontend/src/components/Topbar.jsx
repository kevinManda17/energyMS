import { Menu, Bell, Moon, Sun, LogOut, ChevronDown } from "lucide-react";
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
  const unreadCount = unread?.count ?? unread?.length ?? 0;

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-white/5 dark:bg-[#0B1220]/90">
      <button className="lg:hidden" onClick={toggleSidebar}>
        <Menu size={22} />
      </button>

      <select
        className="input max-w-xs"
        value={currentHouseId || ""}
        onChange={(e) => setHouse(Number(e.target.value))}
      >
        <option value="">Tous les micro-réseaux</option>
        {houseList.map((h) => (
          <option key={h.id} value={h.id}>
            Micro-réseau : {h.name}
          </option>
        ))}
      </select>

      <span className="badge bg-green-50 text-energy dark:bg-green-500/10">
        ● Système : Stable
      </span>

      <div className="ml-auto flex items-center gap-2">
        <button className="btn-ghost p-2" onClick={toggleTheme} title="Thème">
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        <button
          className="relative btn-ghost p-2"
          onClick={() => navigate("/alerts")}
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-danger text-[10px] font-bold text-white">
              {unreadCount}
            </span>
          )}
        </button>

        <div className="flex items-center gap-2 pl-1">
          <div className="grid h-9 w-9 place-items-center rounded-full bg-electric text-sm font-bold text-white">
            {(user?.username || "U").slice(0, 2).toUpperCase()}
          </div>
          <div className="hidden text-sm sm:block">
            <div className="font-semibold leading-tight">{user?.username}</div>
            <div className="text-xs text-slate-400">
              {user?.role === "ADMIN" ? "Administrateur" : "Utilisateur"}
            </div>
          </div>
          <ChevronDown size={14} className="text-slate-400" />
        </div>

        <button
          className="btn-ghost p-2"
          onClick={() => {
            logout();
            navigate("/login");
          }}
          title="Déconnexion"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
