"use client";

import { useEffect } from "react";

import { unlockUiSounds } from "@/lib/ui-sounds";

/**
 * Browsers block audio until a user gesture — resume AudioContext on first interaction.
 */
export function UiSoundUnlock() {
  useEffect(() => {
    let done = false;
    function onGesture() {
      if (done) return;
      done = true;
      void unlockUiSounds();
      window.removeEventListener("pointerdown", onGesture, true);
      window.removeEventListener("keydown", onGesture, true);
    }
    window.addEventListener("pointerdown", onGesture, true);
    window.addEventListener("keydown", onGesture, true);
    return () => {
      window.removeEventListener("pointerdown", onGesture, true);
      window.removeEventListener("keydown", onGesture, true);
    };
  }, []);

  return null;
}
