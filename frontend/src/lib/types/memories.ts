export type MemoryMedia = {
  id: string;
  media_type: string;
  url: string;
  storage_key?: string | null;
  label: string | null;
  sort_order: number;
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

export type EventMemory = {
  id: string;
  event_id: string;
  host_id: string;
  status: string;
  host_recap_note: string | null;
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
  upcoming_events: MemoryUpcomingEvent[];
  share_path: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};
