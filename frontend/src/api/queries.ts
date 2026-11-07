import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { Artist, Page, PendingInvite, PlaylistSummary, Song, TapeSummary } from "./types";

export const useTapes = () => useQuery({ queryKey: ["tapes"], queryFn: () => api<TapeSummary[]>("/api/tapes") });

export const usePendingInvites = () =>
  useQuery({ queryKey: ["invites"], queryFn: () => api<PendingInvite[]>("/api/tapes/invites/pending") });

export const usePlaylists = () =>
  useQuery({ queryKey: ["playlists"], queryFn: () => api<PlaylistSummary[]>("/api/playlists") });

export const useFollows = () => useQuery({ queryKey: ["follows"], queryFn: () => api<Artist[]>("/api/follows") });

export const useFavorites = () =>
  useQuery({ queryKey: ["favorites"], queryFn: () => api<Page<Song>>("/api/favorites?size=100") });

export function useInviteActions() {
  const client = useQueryClient();
  const refresh = () => {
    for (const queryKey of [["invites"], ["tapes"], ["notices"]]) void client.invalidateQueries({ queryKey });
  };
  const join = useMutation({
    mutationFn: (inviteId: string) =>
      api<{ tape_id: string }>(`/api/tapes/claims/${inviteId}/join`, { method: "POST" }),
    onSettled: refresh,
  });
  const dismiss = useMutation({
    mutationFn: (inviteId: string) => api(`/api/tapes/claims/${inviteId}/dismiss`, { method: "POST" }),
    onSettled: refresh,
  });
  return { join, dismiss };
}
