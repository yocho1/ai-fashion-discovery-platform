export type AuthMode = "login" | "register";

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ImageUploadResponse {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  width: number | null;
  height: number | null;
  description: string | null;
  created_at: string;
}

export interface ImageResponse {
  id: number;
  user_id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  width: number | null;
  height: number | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImageListResponse {
  total: number;
  images: ImageResponse[];
}

export interface AnalysisStartResponse {
  message: string;
  analysis_id: number;
  status: string;
  image_id: number;
}

export interface VisionAnalysisResponse {
  id: number;
  image_id: number;
  clothing_type: string | null;
  categories: string[] | null;
  attributes: Record<string, unknown> | null;
  overall_confidence: number | null;
  analysis_status: string;
  error_message: string | null;
  model_used: string;
  created_at: string;
  updated_at: string;
}

export interface VisionAnalysisListResponse {
  total: number;
  analyses: VisionAnalysisResponse[];
}

export interface ClothingItemResponse {
  id: number;
  image_id: number;
  user_id: number;
  clothing_type: string;
  categories: string[] | null;
  attributes: Record<string, unknown> | null;
  visibility: string;
  created_at: string;
}

export interface ClothingItemListResponse {
  total: number;
  items: ClothingItemResponse[];
}

export interface OutfitItemInfo {
  id: number;
  image_id: number;
  clothing_type: string;
}

export interface OutfitRecommendation {
  items: OutfitItemInfo[];
  compatibility_score: number;
  suggestion: string;
}

export interface RecommendationsResponse {
  total: number;
  recommendations: OutfitRecommendation[];
}

export interface OutfitInfo {
  id: number;
  name: string;
  description: string | null;
  items: number[];
  compatibility_score: number | null;
  tags: string[] | null;
  created_at: string;
}

export interface OutfitListResponse {
  total: number;
  outfits: OutfitInfo[];
}

export interface SaveOutfitPayload {
  name: string;
  item_ids: number[];
  description?: string;
  tags?: string[];
}

export interface SaveOutfitResponse {
  message: string;
  outfit_id: number;
  compatibility_score: number;
}

export interface CreateClothingItemPayload {
  image_id: number;
  visibility?: "private" | "public";
}
