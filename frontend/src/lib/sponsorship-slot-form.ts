export const SPONSORSHIP_SLOT_TYPES = [
  { value: "logo_event_page", label: "Logo on event page" },
  { value: "logo_ticket_email", label: "Logo on ticket email" },
  { value: "banner_legacy_page", label: "Banner on Legacy Page" },
  { value: "booth_at_event", label: "Booth at event" },
  { value: "sponsored_vault_content", label: "Sponsored Vault content" },
  { value: "sponsored_memory_page", label: "Sponsored event memory page" },
] as const;

export type SponsorshipSlotFormValues = {
  slot_type: string;
  title: string;
  description: string;
  price: string;
  /** Create only — publish on create when verified. */
  publish?: boolean;
};

export type SponsorshipSlotFilter = "all" | "draft" | "published" | "disabled";

export const SPONSORSHIP_SLOT_FILTERS: {
  value: SponsorshipSlotFilter;
  label: string;
}[] = [
  { value: "all", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "published", label: "Published" },
  { value: "disabled", label: "Disabled" },
];
