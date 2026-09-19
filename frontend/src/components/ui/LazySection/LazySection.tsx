import { useEffect, useRef, useState, type ReactNode } from "react";

interface LazySectionProps {
  children: ReactNode;
  /** Rendered until the section is near the viewport; should reserve its height. */
  placeholder: ReactNode;
  /** How far ahead of the viewport to start loading. */
  rootMargin?: string;
}

/**
 * Mounts `children` only once the placeholder nears the viewport, so a
 * React.lazy chunk inside is not fetched or parsed during the initial load.
 * An in-page link to the section's anchor also triggers the mount.
 */
export function LazySection({ children, placeholder, rootMargin = "600px 0px" }: LazySectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || near) return;
    if (typeof IntersectionObserver === "undefined") {
      setNear(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [near, rootMargin]);

  return near ? <>{children}</> : <div ref={ref}>{placeholder}</div>;
}
