"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/cn";
import { resolveMediaUrl } from "@/lib/media";

type LightboxState = {
  src: string;
  alt: string;
};

type ImageLightboxContextValue = {
  open: (src: string, alt?: string) => void;
  close: () => void;
};

const ImageLightboxContext = createContext<ImageLightboxContextValue | null>(
  null,
);

export function useImageLightbox(): ImageLightboxContextValue {
  const ctx = useContext(ImageLightboxContext);
  if (!ctx) {
    return {
      open: () => undefined,
      close: () => undefined,
    };
  }
  return ctx;
}

/** Attribute markers used by the global click listener. */
export const ENLARGE_SRC_ATTR = "data-enlarge-src";
export const ENLARGE_ALT_ATTR = "data-enlarge-alt";

export function enlargeableAttrs(
  src: string | null | undefined,
  alt = "",
  enlargeSrc?: string | null,
): Record<string, string> | undefined {
  const resolved = src ? resolveMediaUrl(src) : null;
  if (!resolved) return undefined;
  return {
    [ENLARGE_SRC_ATTR]: resolveMediaUrl(enlargeSrc || src) || resolved,
    [ENLARGE_ALT_ATTR]: alt || "Enlarged image",
  };
}

function ImageLightboxOverlay({
  state,
  onClose,
}: {
  state: LightboxState;
  onClose: () => void;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  if (!mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex flex-col bg-ink/95 text-paper backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={state.alt || "Enlarged image"}
    >
      <div className="relative z-20 flex shrink-0 items-center justify-end gap-2 px-3 pb-2 pt-[max(0.75rem,env(safe-area-inset-top))] sm:px-4">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close enlarged image"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-paper/10 text-2xl leading-none text-paper transition hover:bg-paper/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          ×
        </button>
      </div>

      <button
        type="button"
        className="absolute inset-0 z-10 cursor-zoom-out"
        aria-label="Close enlarged image"
        onClick={onClose}
      />

      <div className="relative z-20 flex min-h-0 flex-1 items-center justify-center px-3 pb-[max(1rem,env(safe-area-inset-bottom))] sm:px-6 pointer-events-none">
        {/* eslint-disable-next-line @next/next/no-img-element -- full-res lightbox */}
        <img
          src={state.src}
          alt={state.alt}
          className={cn(
            "pointer-events-auto max-h-[min(88dvh,960px)] max-w-full select-none object-contain",
            "shadow-[0_24px_80px_rgb(0_0_0_/_0.55)]",
          )}
          draggable={false}
        />
      </div>
    </div>,
    document.body,
  );
}

/**
 * Sitewide WhatsApp/TikTok-style image enlarge.
 * Any element with data-enlarge-src opens the lightbox (capture phase so
 * it works inside Links without nested buttons).
 */
export function ImageLightboxProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LightboxState | null>(null);

  const open = useCallback((src: string, alt = "") => {
    const resolved = resolveMediaUrl(src) || src;
    if (!resolved) return;
    setState({ src: resolved, alt: alt || "Enlarged image" });
  }, []);

  const close = useCallback(() => setState(null), []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      const target = e.target;
      if (!(target instanceof Element)) return;
      if (target.closest("[data-enlarge-ignore]")) return;
      const hit = target.closest(`[${ENLARGE_SRC_ATTR}]`);
      if (!hit) return;
      const src = hit.getAttribute(ENLARGE_SRC_ATTR);
      if (!src) return;
      e.preventDefault();
      e.stopPropagation();
      open(src, hit.getAttribute(ENLARGE_ALT_ATTR) || "Enlarged image");
    }

    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [open]);

  const value = useMemo(() => ({ open, close }), [open, close]);

  return (
    <ImageLightboxContext.Provider value={value}>
      {children}
      {state ? <ImageLightboxOverlay state={state} onClose={close} /> : null}
    </ImageLightboxContext.Provider>
  );
}
