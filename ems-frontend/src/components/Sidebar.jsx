import { NavLink } from "react-router-dom";
import {
  Activity,
  Bell,
  Cpu,
  FileText,
  FlaskConical,
  Home,
  LayoutDashboard,
  LineChart,
  MapPin,
  Network,
  Settings,
  Brain,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import Logo from "./Logo";
import { useUIStore } from "../store/ui";
import { housesApi } from "../api/endpoints";

const NAV = [
  { to: "/dashboard",    label: "Dashboard",     icon: LayoutDashboard },
  { to: "/houses",       label: "Micro-réseaux", icon: Network         },
  { to: "/devices",      label: "Équipements",   icon: Cpu             },
  { to: "/measurements", label: "Mesures IoT",   icon: Activity        },
  { to: "/forecasting",  label: "Prévisions",    icon: LineChart       },
  { to: "/decisions",    label: "Décisions",     icon: Brain           },
  { to: "/expert-test",  label: "Test expert",   icon: FlaskConical    },
  { to: "/alerts",       label: "Alertes",       icon: Bell            },
  { to: "/reports",      label: "Rapports",      icon: FileText        },
  { to: "/settings",     label: "Paramètres",    icon: Settings        },
];

export default function Sidebar() {
  const { sidebarOpen, closeSidebar, currentHouseId } = useUIStore();

  const { data: houses } = useQuery({
    queryKey: ["houses"],
    queryFn: housesApi.list,
  });

  const houseList     = houses?.results || houses || [];
  const selectedHouse = houseList.find((h) => h.id === currentHouseId);

  return (
    <>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={closeSidebar}
        />
      )}
      <aside
        className={`fixed z-40 flex h-dvh w-[82vw] max-w-72 flex-col bg-[#0B1220] text-slate-200 shadow-2xl transition-transform lg:static lg:h-screen lg:w-64 lg:shadow-none lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="flex items-start justify-between gap-3 px-5 py-6">
          <Logo light />
          <button
            className="rounded-xl border border-white/10 p-2 text-slate-300 lg:hidden"
            onClick={closeSidebar}
            aria-label="Fermer le menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={closeSidebar}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-electric text-white shadow-lg shadow-electric/20"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon size={17} strokeWidth={2.2} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Widget micro-réseau actif */}
        <div className="m-3 rounded-xl bg-white/5 p-4 text-sm">
          <div className="flex items-center gap-2 text-white">
            <Home size={15} strokeWidth={2.2} className="flex-shrink-0 text-slate-400" />
            <span className="font-semibold truncate">
              {selectedHouse ? selectedHouse.name : "Tous les réseaux"}
            </span>
          </div>
          {selectedHouse?.location && (
            <p className="mt-1.5 flex items-center gap-1 truncate text-xs text-slate-400">
              <MapPin size={11} strokeWidth={2.2} className="flex-shrink-0" />
              {selectedHouse.location}
            </p>
          )}
          <div className="mt-2 text-[10px] text-slate-500">EMS v1.0.0</div>
        </div>
      </aside>
    </>
  );
}
