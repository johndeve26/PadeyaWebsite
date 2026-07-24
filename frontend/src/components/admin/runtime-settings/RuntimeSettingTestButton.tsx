"use client";

import { useState } from "react";

import { Button, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  testRuntimeSettingsCategory,
  type RuntimeSettingTestResult,
} from "@/lib/runtime-settings-api";
import { sanitizePublicMessage } from "@/lib/runtime-settings-display";

type Props = {
  category: string;
  disabled?: boolean;
  label?: string;
  /** Prefer existing specialist test when provided (email/push). */
  onTest?: () => Promise<RuntimeSettingTestResult | void>;
  className?: string;
};

export function RuntimeSettingTestButton({
  category,
  disabled = false,
  label = "Run test",
  onTest,
  className = "",
}: Props) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (disabled || loading) return;
    setLoading(true);
    try {
      const result =
        (await onTest?.()) ?? (await testRuntimeSettingsCategory(category));
      if (!result) {
        toast.push({ tone: "success", title: "Test completed" });
        return;
      }
      if (result.ok) {
        toast.push({
          tone: "success",
          title: "Test passed",
          description: sanitizePublicMessage(
            result.message || result.status || "Integration looks healthy",
          ),
        });
      } else {
        toast.push({
          tone: "danger",
          title: "Test failed",
          description: sanitizePublicMessage(
            result.message || result.detail || result.status || "Check configuration",
          ),
        });
      }
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Test failed",
        description: sanitizePublicMessage(
          err instanceof ApiError ? err.detail : "Could not run test",
        ),
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      disabled={disabled || loading}
      onClick={() => void handleClick()}
      className={className}
    >
      {loading ? "Testing…" : label}
    </Button>
  );
}
