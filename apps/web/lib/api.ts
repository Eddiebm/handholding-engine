import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const niches = {
  create: (data: { name: string; audience: string; monetization_angle: string; notes: string }) =>
    api.post("/niches", data),
  list: () => api.get("/niches"),
};

export const competitors = {
  create: (data: { niche_id: number; title_or_url: string; notes: string }) =>
    api.post("/competitors", data),
  list: (niche_id: number) => api.get(`/competitors/${niche_id}`),
};

export const ideas = {
  generate: (niche_id: number) => api.post("/ideas/generate", { niche_id }),
  list: (niche_id: number) => api.get(`/ideas/${niche_id}`),
  score: (idea_id: number) => api.post(`/ideas/${idea_id}/score`),
  select: (idea_id: number) => api.post(`/ideas/${idea_id}/select`),
};

export const scripts = {
  generate: (idea_id: number) => api.post("/scripts/generate", { idea_id }),
  get: (idea_id: number) => api.get(`/scripts/${idea_id}`),
};

export const assetPacks = {
  generate: (script_id: number) => api.post("/asset-packs/generate", { script_id }),
  get: (script_id: number) => api.get(`/asset-packs/${script_id}`),
};

export const coach = {
  getNextAction: () => api.get("/coach/next-action"),
};

export default api;
