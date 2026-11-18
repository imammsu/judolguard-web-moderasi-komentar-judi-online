import { ShieldCheck } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';

export default function Navbar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-2 text-sm font-medium transition ${
      isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
    }`;

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <span className="text-lg font-bold tracking-tight">JudolGuard</span>
        </Link>
        <div className="flex items-center gap-1">
          <NavLink to="/" end className={linkClass}>
            Beranda
          </NavLink>
          <span
            className="cursor-not-allowed rounded-md px-3 py-2 text-sm font-medium text-slate-400"
            title="Tersedia setelah login OAuth (Part 2)"
          >
            Video
          </span>
          <button
            type="button"
            disabled
            title="Login Google tersedia pada Part 2"
            className="ml-2 cursor-not-allowed rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-500"
          >
            Login dengan Google
          </button>
        </div>
      </nav>
    </header>
  );
}
