export type MediaVariant = {
  url: string;
  width?: number | null;
  height?: number | null;
};

export type PublicMedia = {
  id?: string | null;
  role?: string | null;
  alt?: string | null;
  focal_x?: number | null;
  focal_y?: number | null;
  width?: number | null;
  height?: number | null;
  url?: string | null;
  thumbnail_url?: string | null;
  card_url?: string | null;
  display_url?: string | null;
  full_url?: string | null;
  og_url?: string | null;
  legacy_url?: string | null;
  variants?: Partial<
    Record<"thumbnail" | "card" | "display" | "full" | "og", MediaVariant | string>
  >;
};

export type MediaVariantIntent =
  | "thumbnail"
  | "card"
  | "display"
  | "full"
  | "og";
