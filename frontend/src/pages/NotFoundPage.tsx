import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="py-24 text-center">
      <p className="text-sm font-semibold text-indigo-600">404</p>
      <h1 className="mt-2 text-2xl font-bold">Halaman tidak ditemukan</h1>
      <Link to="/" className="mt-6 inline-block text-sm font-medium text-indigo-600 hover:underline">
        Kembali ke beranda
      </Link>
    </div>
  );
}
