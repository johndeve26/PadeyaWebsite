import type { AIProviderProfile } from "@/lib/types/ai";

/** Sentinel for “try all provider models in order”. */
export const AUTO_MODEL = "__auto__";

export function modelOptionsForProvider(
  provider: AIProviderProfile | undefined,
): { value: string; label: string }[] {
  const options: { value: string; label: string }[] = [
    {
      value: AUTO_MODEL,
      label: "All models (auto — first available wins)",
    },
  ];
  if (!provider) return options;
  const seen = new Set<string>();
  const models = [
    ...(provider.default_model ? [provider.default_model] : []),
    ...(provider.available_models ?? []),
  ];
  for (const m of models) {
    const id = m.trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    options.push({ value: id, label: id });
  }
  return options;
}

export function routeModelToFormValue(model: string | null | undefined): string {
  if (!model || model === "auto" || model === "*") return AUTO_MODEL;
  return model;
}

export function formValueToRouteModel(value: string): string | null {
  if (!value || value === AUTO_MODEL) return null;
  return value;
}
