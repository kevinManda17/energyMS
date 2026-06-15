import { Link, NavLink } from "react-router-dom";
import Logo from "./Logo";

export default function PublicHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-100 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link to="/">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
          <NavLink to="/" className="hover:text-electric">Accueil</NavLink>
          <a href="/#features" className="hover:text-electric">Fonctionnalités</a>
          <NavLink to="/pricing" className="hover:text-electric">Tarifs</NavLink>
          <a href="/#contact" className="hover:text-electric">Contact</a>
        </nav>
        <div className="flex items-center gap-3">
          <Link to="/login" className="btn-ghost">Se connecter</Link>
          <Link to="/register" className="btn-primary">Commencer</Link>
        </div>
      </div>
    </header>
  );
}
