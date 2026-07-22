import { Link } from "react-router-dom";

type BrandLogoProps = {
  className?: string;
  /** Hauteur CSS du wordmark (largeur auto). */
  heightClass?: string;
};

export function BrandLogo({
  className = "",
  heightClass = "h-7 sm:h-8",
}: BrandLogoProps) {
  return (
    <Link
      to="/"
      className={`inline-flex shrink-0 items-center ${className}`}
      aria-label="AlfAhou — Accueil"
    >
      <img
        src="/logo.png"
        alt="AlfAhou"
        width={924}
        height={321}
        className={`${heightClass} w-auto object-contain object-left`}
        decoding="async"
      />
    </Link>
  );
}
