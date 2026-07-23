import { useEffect, useRef, useState } from 'react';

/**
 * IntersectionObserver-based scroll entry animation hook.
 * Adds 'visible' class when element enters viewport.
 */
export function useScrollEntry(options = {}) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('visible');
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px', ...options }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return ref;
}

/**
 * Staggered entry for children. Adds 'visible' class with delay.
 */
export function useStagger(parentRef) {
  useEffect(() => {
    if (!parentRef?.current) return;
    const children = parentRef.current.children;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          Array.from(children).forEach((child, i) => {
            setTimeout(() => child.classList.add('visible'), i * 80);
          });
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(parentRef.current);
    return () => observer.disconnect();
  }, [parentRef]);
}
