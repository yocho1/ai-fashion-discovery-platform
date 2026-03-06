import type {
  AnalysisStartResponse,
  ClothingItemListResponse,
  ClothingItemResponse,
  CreateClothingItemPayload,
  ImageListResponse,
  ImageUploadResponse,
  LoginPayload,
  OutfitListResponse,
  RecommendationsResponse,
  RegisterPayload,
  SaveOutfitPayload,
  SaveOutfitResponse,
  TokenResponse,
  VisionAnalysisListResponse,
  VisionAnalysisResponse,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function buildUrl(path: string, token?: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);

  if (token) {
    url.searchParams.set("authorization", `Bearer ${token}`);
  }

  return url.toString();
}

async function parseError(response: Response): Promise<never> {
  let message = `Request failed with status ${response.status}`;

  try {
    const payload = await response.json();
    const detail = payload?.detail;
    if (typeof detail === "string") {
      message = detail;
    }
  } catch {
    // Keep fallback message
  }

  throw new Error(message);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  const isFormData = options.body instanceof FormData;

  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch(buildUrl(path, token), {
      ...options,
      headers,
      cache: "no-store",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      await parseError(response);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Request timed out — please try again");
    }
    throw error;
  }
}

export async function register(payload: RegisterPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadImage(
  token: string,
  file: File,
  description?: string
): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const query = description
    ? `/images/upload?description=${encodeURIComponent(description)}`
    : "/images/upload";

  return request<ImageUploadResponse>(
    query,
    {
      method: "POST",
      body: formData,
    },
    token
  );
}

export async function listImages(
  token: string,
  limit = 50,
  offset = 0
): Promise<ImageListResponse> {
  return request<ImageListResponse>(
    `/images/my-images?limit=${limit}&offset=${offset}`,
    undefined,
    token
  );
}

export async function analyzeImage(
  token: string,
  imageId: number
): Promise<AnalysisStartResponse> {
  return request<AnalysisStartResponse>(
    "/vision/analyze",
    {
      method: "POST",
      body: JSON.stringify({ image_id: imageId }),
    },
    token
  );
}

export async function getImageAnalysis(
  token: string,
  imageId: number
): Promise<VisionAnalysisResponse> {
  return request<VisionAnalysisResponse>(
    `/vision/analyses/${imageId}`,
    undefined,
    token
  );
}

export async function listAnalyses(
  token: string,
  limit = 50,
  offset = 0
): Promise<VisionAnalysisListResponse> {
  return request<VisionAnalysisListResponse>(
    `/vision/my-analyses?limit=${limit}&offset=${offset}`,
    undefined,
    token
  );
}

export async function createClothingItem(
  token: string,
  payload: CreateClothingItemPayload
): Promise<ClothingItemResponse> {
  return request<ClothingItemResponse>(
    "/recommendations/clothing-items",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

export async function listClothingItems(
  token: string,
  limit = 50,
  offset = 0
): Promise<ClothingItemListResponse> {
  return request<ClothingItemListResponse>(
    `/recommendations/clothing-items?limit=${limit}&offset=${offset}`,
    undefined,
    token
  );
}

export async function getRecommendations(
  token: string,
  referenceImageId: number,
  limit = 5
): Promise<RecommendationsResponse> {
  return request<RecommendationsResponse>(
    "/recommendations/recommendations",
    {
      method: "POST",
      body: JSON.stringify({ reference_image_id: referenceImageId, limit }),
    },
    token
  );
}

export async function saveOutfit(
  token: string,
  payload: SaveOutfitPayload
): Promise<SaveOutfitResponse> {
  return request<SaveOutfitResponse>(
    "/recommendations/outfits",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

export async function listOutfits(
  token: string,
  limit = 50,
  offset = 0
): Promise<OutfitListResponse> {
  return request<OutfitListResponse>(
    `/recommendations/outfits?limit=${limit}&offset=${offset}`,
    undefined,
    token
  );
}

export async function deleteOutfit(token: string, outfitId: number): Promise<void> {
  return request<void>(
    `/recommendations/outfits/${outfitId}`,
    {
      method: "DELETE",
    },
    token
  );
}

export function getImageUrl(imageId: number, token: string): string {
  return buildUrl(`/images/${imageId}/file`, token);
}
