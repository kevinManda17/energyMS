import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Network,
  Cpu,
  Activity,
  LineChart,
  Workflow,
  Bell,
  FileText,
  Settings,
  Home,
  X,
} from "lucide-react";
import Logo from "./Logo";
import { useUIStore } from "../store/ui";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/houses", label: "Micro-réseaux", icon: Network },
  { to: "/devices", label: "Équipements", icon: Cpu },
  { to: "/measurements", label: "Mesures IoT", icon: Activity },
  { to: "/forecasting", label: "Prévisions", icon: LineChart },
  { to: "/decisions", label: "Décisions", icon: Workflow },
  { to: "/alerts", label: "Alertes", icon: Bell },
  { to: "/reports", label: "Rapports", icon: FileText },
  // { to: "/pricing", label: "Tarifs", icon: Tags },
  { to: "/settings", label: "Paramètres", icon: Settings },
];

export default function Sidebar() {
  const { sidebarOpen, closeSidebar } = useUIStore();

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

        <nav className="flex-1 space-y-1 overflow-y-auto px-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={closeSidebar}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-electric text-white shadow-lg shadow-electric/30"
                    : "text-slate-300 hover:bg-white/5"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="m-3 rounded-xl bg-white/5 p-4 text-sm">
          <div className="flex items-center gap-2 text-white">
            <Home size={16} /> <span className="font-semibold">Micro-réseau</span>
          </div>
          <div className="mt-2 flex items-center gap-2 text-xs text-energy">
            <span className="h-2 w-2 rounded-full bg-energy" /> Connecté
          </div>
          <div className="mt-1 text-xs text-slate-400">EMS v1.0.0</div>
        </div>
      </aside>
    </>
  );
}
