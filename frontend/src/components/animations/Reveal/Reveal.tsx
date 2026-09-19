import { useEffect, useRef, useState, type ReactNode } from "react";
import styles from "./Reveal.module.css";

type Delay = 0 | 1 | 2 | 3 | 4 | 5;

interface RevealProps {
  children: ReactNode;
  /** Stagger step; each step adds 80ms. */
  delay?: Delay;
  as?: "div" | "li";
  className?: string;
}

/**
 * Fades content in and lifts it 12px the first time it scrolls into view.
 * Content is shown immediately when IntersectionObserver is missing; reduced
 * motion is handled by the global rule, which makes the transition instant.
 */
export function Reveal({ children, delay = 0, as: Tag = "div", className }: RevealProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.1 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const cls = [styles.reveal, styles[`d${delay}`], visible && styles.visible, className].filter(Boolean).join(" ");

  return (
    <Tag ref={ref as never} className={cls}>
      {children}
    </Tag>
  );
}
