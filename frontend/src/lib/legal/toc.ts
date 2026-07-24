import type { LegalTocItem } from "@/components/legal/LegalDocument";

/** Build TOC items from section id/title pairs. */
export function legalToc(
  ...sections: readonly { id: string; title: string }[]
): LegalTocItem[] {
  return sections.map(({ id, title }) => ({ id, title }));
}
