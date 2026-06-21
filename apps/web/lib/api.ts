import axios from "axios";

const api = axios.create({
  baseURL: "/api/proxy",
  headers: {
    "Content-Type": "application/json",
  },
});

// Intercept requests to add path parameter
api.interceptors.request.use((config) => {
  let path = config.url || "";

  // Handle query parameters for specific endpoints
  if (config.method === "post" && config.data) {
    if (path === "/asset-packs/generate" && config.data.script_id) {
      path = `/asset-packs/generate?script_id=${config.data.script_id}`;
      config.data = undefined;
    }
    if (path === "/ideas/generate" && config.data.niche_id) {
      path = `/ideas/generate?niche_id=${config.data.niche_id}`;
      config.data = undefined;
    }
    if (path === "/scripts/generate" && config.data.idea_id) {
      path = `/scripts/generate?idea_id=${config.data.idea_id}`;
      config.data = undefined;
    }
  }

  config.url = `?path=${encodeURIComponent(path)}`;
  return config;
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
