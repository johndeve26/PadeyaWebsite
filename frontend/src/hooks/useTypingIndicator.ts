"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useMessageSocket } from "@/hooks/useMessageSocket";
import type { MessagingSocketEvent } from "@/lib/messaging/socket-types";

const PEER_TYPING_TTL_MS = 4_500;
const START_DEBOUNCE_MS = 300;
const STOP_IDLE_MS = 2_500;

/**
 * Peer typing state + local typing.start / typing.stop with debounce.
 * Stops on idle, blur (via setTyping(false)), and navigation/unmount.
 */
export function useTypingIndicator(threadId: string | null | undefined): {
  peerTyping: boolean;
  peerDisplayName: string | null;
  setTyping: (isTyping: boolean) => void;
} {
  const [peerTyping, setPeerTyping] = useState(false);
  const [peerDisplayName, setPeerDisplayName] = useState<string | null>(null);
  const peerTimer = useRef<number | undefined>(undefined);
  const startDebounce = useRef<number | undefined>(undefined);
  const stopIdle = useRef<number | undefined>(undefined);
  const localActive = useRef(false);
  const activeThread = threadId || "";

  const clearPeer = useCallback(() => {
    if (peerTimer.current) window.clearTimeout(peerTimer.current);
    peerTimer.current = undefined;
    setPeerTyping(false);
    setPeerDisplayName(null);
  }, []);

  const onEvent = useCallback(
    (event: MessagingSocketEvent) => {
      if (event.type !== "message.typing") return;
      if (!activeThread || event.thread_id !== activeThread) return;
      if (event.is_typing) {
        setPeerTyping(true);
        const name = (event.display_name || "").trim();
        setPeerDisplayName(name || null);
        if (peerTimer.current) window.clearTimeout(peerTimer.current);
        peerTimer.current = window.setTimeout(clearPeer, PEER_TYPING_TTL_MS);
      } else {
        clearPeer();
      }
    },
    [activeThread, clearPeer],
  );

  const { sendTyping } = useMessageSocket(onEvent, Boolean(activeThread));

  const sendStop = useCallback(() => {
    if (!activeThread) return;
    if (startDebounce.current) {
      window.clearTimeout(startDebounce.current);
      startDebounce.current = undefined;
    }
    if (stopIdle.current) {
      window.clearTimeout(stopIdle.current);
      stopIdle.current = undefined;
    }
    if (localActive.current) {
      localActive.current = false;
      sendTyping(activeThread, false);
    }
  }, [activeThread, sendTyping]);

  useEffect(() => {
    let alive = true;
    queueMicrotask(() => {
      if (alive) clearPeer();
    });
    return () => {
      alive = false;
      clearPeer();
      // typing.stop on navigation / unmount
      sendStop();
    };
  }, [activeThread, clearPeer, sendStop]);

  const setTyping = useCallback(
    (isTyping: boolean) => {
      if (!activeThread) return;
      if (!isTyping) {
        sendStop();
        return;
      }

      // Debounce typing.start so single taps don't spam the peer.
      if (!localActive.current && !startDebounce.current) {
        startDebounce.current = window.setTimeout(() => {
          startDebounce.current = undefined;
          localActive.current = true;
          sendTyping(activeThread, true);
        }, START_DEBOUNCE_MS);
      }

      if (stopIdle.current) window.clearTimeout(stopIdle.current);
      stopIdle.current = window.setTimeout(() => {
        sendStop();
      }, STOP_IDLE_MS);
    },
    [activeThread, sendStop, sendTyping],
  );

  return { peerTyping, peerDisplayName, setTyping };
}
