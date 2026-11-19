import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { cx } from "./ui";
import {
  IconChat, IconDashboard, IconLogout, IconMap, IconMenu, IconPlane, IconSliders, IconSun, IconTicket,
} from "./icons";

const NAV = [
  { to: "/", label: "Dashboard", icon: IconDashboard, end: true },
  { to: "/asistente", label: "Asistente", icon: IconChat },
  { to: "/vuelos", label: "Vuelos", icon: IconPlane },
  { to: "/clima", label: "Clima", icon: IconSun },
  { to: "/viajes", label: "Mis viajes", icon: IconMap },
  { to: "/reservas", label: "Reservas", icon: IconTicket },
  { to: "/preferencias", label: "Preferencias", icon: IconSliders },
];

export function Logo() {
  return (
    <div className="flex items-center gap-2">
      <img src="/favicon.svg" alt="" className="h-8 w-8" />
      <span className="text-lg font-semibold text-slate-900">
        TripPlanner <span className="text-brand-600">AI</span>
      </span>
    </div>
  );
}

export default function Layout() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);

  const nav = (
    <nav className="flex flex-1 flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            cx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )
          }
        >
          <Icon className="h-5 w-5" />
          {label}
        </NavLink>
      ))}
    </nav>
  );

  const userBox = (
    <div className="border-t border-slate-200 pt-4">
      <p className="truncate text-sm font-medium text-slate-800">{user?.name || "Viajero"}</p>
      <p className="truncate text-xs text-slate-500">{user?.email}</p>
      <button
        onClick={signOut}
        className="mt-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
      >
        <IconLogout className="h-4 w-4" /> Cerrar sesión
      </button>
    </div>
  );

  return (
    <div className="flex h-full">
      {/* Barra lateral (escritorio) */}
      <aside className="hidden w-64 shrink-0 flex-col gap-6 border-r border-slate-200 bg-white p-4 lg:flex">
        <Logo />
        {nav}
        {userBox}
      </aside>

      {/* Menú móvil */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col gap-6 bg-white p-4">
            <Logo />
            {nav}
            {userBox}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <Logo />
          <button onClick={() => setOpen(true)} className="rounded-lg p-2 hover:bg-slate-100" aria-label="Abrir menú">
            <IconMenu className="h-6 w-6" />
          </button>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
