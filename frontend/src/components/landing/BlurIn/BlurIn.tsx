import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";
import styles from "./BlurIn.module.css";

type Delay = 0 | 1 | 2 | 3 | 4;

export function BlurIn({
  children,
  as: Tag = "div",
  delay = 0,
  className,
}: {
  children: ReactNode;
  as?: ElementType;
  delay?: Delay;
  className?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setShown(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setShown(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag ref={ref} className={[styles.blur, styles[`d${delay}`], shown && styles.shown, className].filter(Boolean).join(" ")}>
      {children}
    </Tag>
  );
}
