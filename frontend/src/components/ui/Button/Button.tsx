import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Spinner } from "../Spinner/Spinner";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "inverse";
type Size = "md" | "lg";

interface BaseProps {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  className?: string;
  fullWidth?: boolean;
  onClick?: () => void;
}

interface ActionProps {
  type?: "button" | "submit";
  /** Shows a spinner and blocks further clicks while a request is in flight. */
  loading?: boolean;
  disabled?: boolean;
}

type ButtonProps =
  | (BaseProps & { to: string; href?: never; type?: never; loading?: never; disabled?: never })
  | (BaseProps & { href: string; to?: never; type?: never; loading?: never; disabled?: never })
  | (BaseProps & ActionProps & { to?: never; href?: never });

/** Renders a router Link (`to`), an anchor (`href`), or a native button. */
export function Button({
  children,
  variant = "primary",
  size = "md",
  className,
  fullWidth,
  onClick,
  ...rest
}: ButtonProps) {
  const cls = [styles.button, styles[variant], styles[size], fullWidth && styles.full, className]
    .filter(Boolean)
    .join(" ");

  if ("to" in rest && rest.to) {
    return (
      <Link to={rest.to} className={cls} onClick={onClick}>
        {children}
      </Link>
    );
  }
  if ("href" in rest && rest.href) {
    return (
      <a href={rest.href} className={cls} onClick={onClick}>
        {children}
      </a>
    );
  }
  const { type = "button", loading = false, disabled = false } = rest as ActionProps;
  return (
    <button type={type} className={cls} onClick={onClick} disabled={disabled || loading} aria-busy={loading || undefined}>
      {loading && <Spinner />}
      {children}
    </button>
  );
}
