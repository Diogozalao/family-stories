import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Home } from "lucide-react";
import Logo from "../components/brand/Logo";

export default function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-stone-50 px-4 py-12 dark:bg-stone-950">
      <Logo size={32} />
      <div className="mt-10 text-center">
        <p className="font-serif text-7xl font-semibold tracking-tight text-stone-900 dark:text-stone-100">
          404
        </p>
        <p className="mt-4 text-stone-600 dark:text-stone-400">
          {t("notFound.lead")}
        </p>
        <Link to="/" className="btn btn-primary mt-8">
          <Home className="h-4 w-4" />
          <span>{t("notFound.backHome")}</span>
        </Link>
      </div>
    </div>
  );
}
