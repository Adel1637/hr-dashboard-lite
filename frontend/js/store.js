// État partagé entre les vues : métadonnées et filtres du tableau de bord.
import { api } from "./core.js";

export const state = { meta: null };

export async function refreshMeta() {
  state.meta = await api("/api/meta");
  return state.meta;
}
