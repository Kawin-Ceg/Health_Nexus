import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "inverse";
type Size = "md" | "lg";

interface BaseProps {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  className?: string;
  onClick?: () => void;
}

type ButtonProps =
  | (BaseProps & { to: string; href?: never; type?: never })
  | (BaseProps & { href: string; to?: never; type?: never })
  | (BaseProps & { type?: "button" | "submit"; to?: never; href?: never });

/** Renders a router Link (`to`), an anchor (`href`), or a native button. */
export function Button({ children, variant = "primary", size = "md", className, onClick, ...rest }: ButtonProps) {
  const cls = [styles.button, styles[variant], styles[size], className].filter(Boolean).join(" ");

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
  return (
    <button type={("type" in rest && rest.type) || "button"} className={cls} onClick={onClick}>
      {children}
    </button>
  );
}
