export type Role = "listener" | "composer" | "admin";

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  status: string;
  created_at: string;
};

export type Page<T> = { items: T[]; total: number; page: number; size: number };

export type Song = {
  id: string;
  title: string;
  artist_id: string;
  artist: string;
  album: string | null;
  duration: number;
  cover_url: string | null;
  source: "jamendo" | "local";
  license: string | null;
  license_url: string | null;
  jamendo_url: string | null;
  genres: string[];
  status: string;
  available: boolean;
};

export type TapeSummary = {
  id: string;
  title: string;
  color: string;
  is_creator: boolean;
  member_count: number;
  track_count: number;
  max_tracks: number;
};

export type PendingInvite = {
  invite_id: string;
  tape_id: string;
  title: string;
  color: TapeSummary["color"];
  inviter: string | null;
  expires_at: string | null;
};

export type PlaylistSummary = { id: string; owner_id: string; name: string; is_public: boolean; created_at: string };

export type PlaylistDetail = PlaylistSummary & { degraded: boolean; songs: Song[] };

export type Artist = {
  id: string;
  name: string;
  source: string;
  bio: string | null;
  photo_url: string | null;
  links: Record<string, string> | null;
};

export type HistoryItem = { playback_id: string; listened_seconds: number; started_at: string; song: Song | null };

export type Releases = {
  scheduled: { song_id: string; title: string; artist_id: string; artist: string; publish_at: string }[];
  published: { song: Song; published_at: string }[];
  degraded: boolean;
};

export type Notices = {
  unread: number;
  degraded: boolean;
  items: (
    | { type: "release"; song: Song; published_at: string }
    | ({ type: "invite" } & PendingInvite)
  )[];
};

export type TapeTrack = {
  id: string;
  position: number;
  side: "A" | "B";
  song: Song;
  added_by: string;
  added_by_name: string | null;
  dedication: string | null;
  can_remove: boolean;
};

export type TapeInviteRow = { id: string; expires_at: string | null; max_uses: number; uses: number };

export type TapeDetail = {
  id: string;
  title: string;
  color: TapeSummary["color"];
  creator_id: string;
  is_creator: boolean;
  version: number;
  created_at: string;
  max_tracks: number;
  max_members: number;
  degraded: boolean;
  members: { user_id: string; name: string | null; joined_at: string }[];
  tracks: TapeTrack[];
  invites: TapeInviteRow[];
};
