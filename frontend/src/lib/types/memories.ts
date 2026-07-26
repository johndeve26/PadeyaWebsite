export type MemoryMedia = {
  id: string;
  media_type: string;
  url: string;
  thumbnail_url?: string | null;
  storage_key?: string | null;
  label: string | null;
  caption?: string | null;
  sort_order: number;
  uploader_role?: "host" | "fan" | string;
  is_cover?: boolean;
  status?: string;
  width?: number | null;
  height?: number | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  attribution?: string | null;
  verified_attendee?: boolean;
  created_at: string;
};

export type MemoryAttendance = {
  tickets_sold: number;
  checked_in: number;
  check_in_rate: string | number | null;
};

export type MemoryUpcomingEvent = {
  id: string;
  title: string;
  slug: string;
  start_datetime: string;
  city: string | null;
  banner_url: string | null;
};

export type MemoryCounts = {
  memory_count: number;
  host_memory_count: number;
  community_memory_count: number;
  contributor_count: number;
};

export type EventMemory = {
  id: string;
  event_id: string;
  host_id: string;
  status: string;
  host_recap_note: string | null;
  external_gallery_url?: string | null;
  external_gallery_label?: string | null;
  moderation_status: string;
  event_title: string;
  event_slug: string;
  start_datetime: string;
  end_datetime: string;
  venue_name: string | null;
  city: string | null;
  banner_url: string | null;
  host_display_name: string;
  host_username: string;
  attendance: MemoryAttendance;
  verified_rating: string | number | null;
  review_count: number;
  top_reviews: {
    id: string;
    rating: number;
    title: string | null;
    body: string;
    reviewer_name: string | null;
    created_at: string;
  }[];
  media: MemoryMedia[];
  host_media?: MemoryMedia[];
  community_media?: MemoryMedia[];
  counts?: MemoryCounts;
  upcoming_events: MemoryUpcomingEvent[];
  share_path: string;
  memories_path?: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  seo_indexable?: boolean;
};

export type MemoryAlbumCard = {
  event_id: string;
  event_slug: string;
  event_title: string;
  start_datetime: string;
  end_datetime: string;
  city: string | null;
  host_display_name: string;
  host_username: string;
  cover_url: string | null;
  cover_thumbnail_url: string | null;
  counts: MemoryCounts;
  memories_path: string;
  share_path: string;
};

export type MemoryAlbumsResponse = {
  items: MemoryAlbumCard[];
  next_cursor: string | null;
};

export type MemoryEligibility = {
  authenticated: boolean;
  ticket_verified: boolean;
  event_started: boolean;
  can_upload: boolean;
  role: string | null;
  used: number;
  limit: number;
  remaining: number;
  host_limit: number;
};

export type AdminMemoryPhoto = {
  id: string;
  memory_id: string;
  event_id: string;
  event_title: string;
  event_slug: string;
  uploader_role: string;
  uploader_user_id: string | null;
  status: string;
  url: string;
  thumbnail_url: string | null;
  caption: string | null;
  created_at: string;
  hidden_by: string | null;
};

export const EXTERNAL_GALLERY_LABELS = [
  { value: "instagram", label: "Instagram" },
  { value: "google_drive", label: "Google Drive" },
  { value: "official", label: "Official gallery" },
  { value: "other", label: "Other" },
] as const;
