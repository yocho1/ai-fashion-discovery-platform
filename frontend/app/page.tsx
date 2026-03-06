"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  analyzeImage,
  createClothingItem,
  deleteOutfit,
  getImageAnalysis,
  getImageUrl,
  getRecommendations,
  listAnalyses,
  listClothingItems,
  listImages,
  listOutfits,
  login,
  register,
  saveOutfit,
  uploadImage,
} from "@/lib/api";
import type {
  AuthMode,
  ClothingItemResponse,
  ImageResponse,
  OutfitInfo,
  OutfitRecommendation,
  TokenResponse,
  User,
  VisionAnalysisResponse,
} from "@/lib/types";

const TOKEN_STORAGE_KEY = "afd_access_token";
const USER_STORAGE_KEY = "afd_user";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error";
}

function statusClass(status: string): string {
  if (status === "completed") {
    return "badge badge-success";
  }
  if (status === "failed") {
    return "badge badge-error";
  }
  return "badge badge-warning";
}

/* ─── SVG Icons ─── */

function IconDiamond() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 2.41 0 0 0 0-3.41l-7.59-7.59a2.41 2.41 0 0 0-3.41 0Z" />
    </svg>
  );
}

function IconUpload() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function IconStar() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function IconHanger() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 20h20L12 4" /><path d="M12 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />
    </svg>
  );
}

function IconSave() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" />
    </svg>
  );
}

export default function HomePage() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");

  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const [images, setImages] = useState<ImageResponse[]>([]);
  const [analysesByImage, setAnalysesByImage] = useState<Record<number, VisionAnalysisResponse>>({});
  const [clothingItems, setClothingItems] = useState<ClothingItemResponse[]>([]);
  const [recommendations, setRecommendations] = useState<OutfitRecommendation[]>([]);
  const [outfits, setOutfits] = useState<OutfitInfo[]>([]);

  const [selectedImageId, setSelectedImageId] = useState<number | null>(null);
  const [newOutfitName, setNewOutfitName] = useState("");

  const [uploadFileValue, setUploadFileValue] = useState<File | null>(null);
  const [uploadDescription, setUploadDescription] = useState("");

  const [busy, setBusy] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const clearMessages = useCallback(() => {
    setSuccessMessage("");
    setErrorMessage("");
  }, []);

  const persistAuth = useCallback((auth: TokenResponse) => {
    setToken(auth.access_token);
    setCurrentUser(auth.user);
    localStorage.setItem(TOKEN_STORAGE_KEY, auth.access_token);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(auth.user));
  }, []);

  const loadDashboardData = useCallback(
    async (activeToken: string) => {
      const [imagesResponse, analysesResponse, clothingResponse, outfitsResponse] = await Promise.all([
        listImages(activeToken),
        listAnalyses(activeToken),
        listClothingItems(activeToken),
        listOutfits(activeToken),
      ]);

      setImages(imagesResponse.images);
      setClothingItems(clothingResponse.items);
      setOutfits(outfitsResponse.outfits);

      const analysesMap: Record<number, VisionAnalysisResponse> = {};
      for (const analysis of analysesResponse.analyses) {
        analysesMap[analysis.image_id] = analysis;
      }
      setAnalysesByImage(analysesMap);

      if (!selectedImageId && imagesResponse.images.length > 0) {
        setSelectedImageId(imagesResponse.images[0].id);
      }
    },
    [selectedImageId]
  );

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    const storedUser = localStorage.getItem(USER_STORAGE_KEY);

    if (!storedToken || !storedUser) {
      return;
    }

    try {
      const parsedUser = JSON.parse(storedUser) as User;
      setToken(storedToken);
      setCurrentUser(parsedUser);
    } catch {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    const hydrate = async () => {
      try {
        await loadDashboardData(token);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(getErrorMessage(error));
        }
      }
    };

    void hydrate();

    return () => {
      cancelled = true;
    };
  }, [token, loadDashboardData]);

  const handleAuthSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearMessages();
    setBusy(true);

    try {
      const authResult =
        authMode === "register"
          ? await register({
              email,
              password,
              username,
              full_name: fullName || undefined,
            })
          : await login({ email, password });

      persistAuth(authResult);
      setSuccessMessage("Authentication successful");
      setPassword("");
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);

    setToken(null);
    setCurrentUser(null);
    setImages([]);
    setAnalysesByImage({});
    setClothingItems([]);
    setRecommendations([]);
    setOutfits([]);
    setSelectedImageId(null);
    clearMessages();
  };

  const handleUploadImage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!token || !uploadFileValue) {
      setErrorMessage("Select an image file before uploading");
      return;
    }

    clearMessages();
    setBusy(true);

    try {
      await uploadImage(token, uploadFileValue, uploadDescription || undefined);
      await loadDashboardData(token);
      setUploadFileValue(null);
      setUploadDescription("");
      setSuccessMessage("Image uploaded successfully");
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleAnalyzeImage = async (imageId: number) => {
    if (!token) {
      return;
    }

    clearMessages();
    setBusy(true);

    try {
      // Start analysis (returns immediately with 202 ACCEPTED)
      await analyzeImage(token, imageId);
      setSuccessMessage("Analysis started... checking progress");

      // Poll for completion (max 2 minutes)
      const maxAttempts = 120;
      let attempts = 0;
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
        
        try {
          const analysis = await getImageAnalysis(token, imageId);
          
          if (analysis.analysis_status === "completed") {
            await loadDashboardData(token);
            setSuccessMessage(`Analysis completed for image #${imageId}`);
            break;
          } else if (analysis.analysis_status === "failed") {
            setErrorMessage(`Analysis failed: ${analysis.error_message || 'Unknown error'}`);
            await loadDashboardData(token);
            break;
          }
          // Still pending, continue polling
          attempts++;
        } catch (e) {
          // Keep polling if fetch fails
          attempts++;
        }
      }
      
      if (attempts >= maxAttempts) {
        setErrorMessage("Analysis timed out after 2 minutes");
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleCreateClothingItem = async (imageId: number) => {
    if (!token) {
      return;
    }

    clearMessages();
    setBusy(true);

    try {
      await createClothingItem(token, { image_id: imageId, visibility: "private" });
      await loadDashboardData(token);
      setSuccessMessage(`Image #${imageId} added to your closet`);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleGenerateRecommendations = async () => {
    if (!token || !selectedImageId) {
      setErrorMessage("Select a reference image first");
      return;
    }

    clearMessages();
    setBusy(true);

    try {
      const response = await getRecommendations(token, selectedImageId, 5);
      setRecommendations(response.recommendations);
      setSuccessMessage(`Generated ${response.total} recommendation(s)`);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
      setRecommendations([]);
    } finally {
      setBusy(false);
    }
  };

  const handleSaveRecommendation = async (recommendation: OutfitRecommendation, index: number) => {
    if (!token) {
      return;
    }

    clearMessages();
    setBusy(true);

    const defaultName = `AI Look ${index + 1}`;

    try {
      await saveOutfit(token, {
        name: newOutfitName.trim() || defaultName,
        item_ids: recommendation.items.map((item) => item.id),
        description: recommendation.suggestion,
        tags: ["ai-generated"],
      });

      await loadDashboardData(token);
      setSuccessMessage("Outfit saved successfully");
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteOutfit = async (outfitId: number) => {
    if (!token) {
      return;
    }

    clearMessages();
    setBusy(true);

    try {
      await deleteOutfit(token, outfitId);
      await loadDashboardData(token);
      setSuccessMessage(`Outfit #${outfitId} deleted`);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const imageOptions = useMemo(
    () => images.map((image) => ({ value: image.id, label: `${image.id} - ${image.original_filename}` })),
    [images]
  );

  const analyzedCount = useMemo(
    () => Object.values(analysesByImage).filter((a) => a.analysis_status === "completed").length,
    [analysesByImage]
  );

  /* ─── Auth Screen ─── */
  if (!token || !currentUser) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-logo">
            <IconDiamond />
            FASHIONAI
          </div>
          <p className="auth-subtitle">AI-powered style discovery &amp; outfit recommendations</p>

          {errorMessage && <div className="toast toast-error">{errorMessage}</div>}
          {successMessage && <div className="toast toast-success">{successMessage}</div>}

          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${authMode === "login" ? "active" : ""}`}
              onClick={() => setAuthMode("login")}
              disabled={busy}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-tab ${authMode === "register" ? "active" : ""}`}
              onClick={() => setAuthMode("register")}
              disabled={busy}
            >
              Create Account
            </button>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            {authMode === "register" && (
              <>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="Username"
                  minLength={3}
                  required
                />
                <input
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Full name (optional)"
                />
              </>
            )}

            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Email address"
              required
            />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              minLength={8}
              required
            />

            <button type="submit" className="btn-primary btn-full" disabled={busy}>
              {busy && <span className="spinner" />}
              {busy ? "Please wait..." : (authMode === "register" ? "Create Account" : "Sign In")}
            </button>
          </form>
        </div>
      </div>
    );
  }

  /* ─── Dashboard ─── */
  return (
    <>
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <IconDiamond />
          FASHIONAI
        </div>
        <div className="navbar-user">
          <span>{currentUser.username}</span>
          <button className="btn-outline btn-sm" style={{ color: "#fff", borderColor: "rgba(255,255,255,0.2)" }} type="button" onClick={handleLogout} disabled={busy}>
            Sign Out
          </button>
        </div>
      </nav>

      <div className="page-container">
        {/* Toast Messages */}
        {errorMessage && <div className="toast toast-error">{errorMessage}</div>}
        {successMessage && <div className="toast toast-success">{successMessage}</div>}

        {/* Stats Bar */}
        <div className="stats-bar">
          <div className="stat-card">
            <div className="stat-number">{images.length}</div>
            <div className="stat-label">Images</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{analyzedCount}</div>
            <div className="stat-label">Analyzed</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{clothingItems.length}</div>
            <div className="stat-label">In Closet</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{outfits.length}</div>
            <div className="stat-label">Outfits</div>
          </div>
        </div>

        {/* ── Upload Section ── */}
        <div className="section-header">
          <div>
            <h2 className="section-title">Upload</h2>
            <p className="section-subtitle">Add fashion images to your collection</p>
          </div>
        </div>

        <div className="card">
          <form className="column" onSubmit={handleUploadImage}>
            <label htmlFor="file-input" className="upload-zone" tabIndex={0} role="button" onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") document.getElementById("file-input")?.click(); }}>
              <div className="upload-icon">
                <IconUpload />
              </div>
              <div className="upload-label">
                {uploadFileValue ? uploadFileValue.name : "Click to select an image"}
              </div>
              <div className="upload-hint">JPG, PNG, or WebP</div>
              <input
                id="file-input"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => setUploadFileValue(event.target.files?.[0] ?? null)}
                style={{ display: "none" }}
                required
              />
            </label>
            <input
              value={uploadDescription}
              onChange={(event) => setUploadDescription(event.target.value)}
              placeholder="Description (optional)"
              maxLength={512}
            />
            <button type="submit" className="btn-primary" disabled={busy || !uploadFileValue}>
              {busy && <span className="spinner" />}
              {busy ? "Uploading..." : "Upload Image"}
            </button>
          </form>
        </div>

        <hr className="section-divider" />

        {/* ── Image Gallery ── */}
        <div className="section-header">
          <div>
            <h2 className="section-title">Your Images</h2>
            <p className="section-subtitle">{images.length} image{images.length === 1 ? "" : "s"} in your collection</p>
          </div>
        </div>

        {images.length === 0 ? (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">📸</div>
              <p className="empty-state-text">No images yet. Upload your first fashion image above!</p>
            </div>
          </div>
        ) : (
          <div className="image-grid">
            {images.map((image) => {
              const analysis = analysesByImage[image.id];
              return (
                <div className="image-card" key={image.id}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    className="image-card-thumb"
                    src={getImageUrl(image.id, token)}
                    alt={image.original_filename}
                    loading="lazy"
                  />
                  <div className="image-card-body">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <div className="image-card-title">{image.original_filename}</div>
                      <span className={statusClass(analysis?.analysis_status ?? "pending")}>
                        {analysis?.analysis_status ?? "new"}
                      </span>
                    </div>
                    <div className="image-card-meta">
                      {image.width ?? "?"}×{image.height ?? "?"} &bull; {image.mime_type?.split("/")[1]?.toUpperCase()}
                    </div>

                    {analysis?.clothing_type && (
                      <div className="image-card-detected">
                        <IconHanger />
                        {analysis.clothing_type}
                      </div>
                    )}

                    <div className="image-card-actions">
                      <button
                        className="btn-secondary btn-sm"
                        type="button"
                        onClick={() => handleAnalyzeImage(image.id)}
                        disabled={busy}
                      >
                        <IconSearch /> Analyze
                      </button>
                      <button
                        className="btn-outline btn-sm"
                        type="button"
                        onClick={() => handleCreateClothingItem(image.id)}
                        disabled={busy}
                      >
                        <IconHanger /> Add to Closet
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <hr className="section-divider" />

        {/* ── AI Recommendations ── */}
        <div className="section-header">
          <div>
            <h2 className="section-title">AI Recommendations</h2>
            <p className="section-subtitle">Get personalized outfit suggestions</p>
          </div>
        </div>

        <div className="card">
          <div className="select-with-btn mb-16">
            <select
              value={selectedImageId ?? ""}
              onChange={(event) => setSelectedImageId(Number(event.target.value))}
              disabled={busy || imageOptions.length === 0}
            >
              {imageOptions.length === 0 ? (
                <option value="">No images available</option>
              ) : (
                imageOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))
              )}
            </select>
            <button
              type="button"
              className="btn-primary"
              onClick={handleGenerateRecommendations}
              disabled={busy || imageOptions.length === 0}
            >
              {busy && <span className="spinner" />}
              Generate
            </button>
          </div>

          <input
            value={newOutfitName}
            onChange={(event) => setNewOutfitName(event.target.value)}
            placeholder="Custom outfit name (optional)"
            maxLength={255}
            className="mb-16"
          />

          {recommendations.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">✨</div>
              <p className="empty-state-text">Select a reference image and generate AI-powered outfit ideas</p>
            </div>
          ) : (
            <div className="reco-grid">
              {recommendations.map((recommendation, index) => (
                <div className="reco-card" key={`${recommendation.suggestion}-${index}`}>
                  <div className="reco-header">
                    <div className="reco-title">Look {index + 1}</div>
                    <span className="reco-score">
                      <IconStar />
                      {recommendation.compatibility_score.toFixed(2)}
                    </span>
                  </div>
                  <p className="reco-suggestion">{recommendation.suggestion}</p>
                  <p className="reco-items">
                    {recommendation.items.map((item) => `${item.clothing_type} (#${item.id})`).join(" • ")}
                  </p>
                  <button
                    type="button"
                    className="btn-gold btn-sm btn-full"
                    onClick={() => handleSaveRecommendation(recommendation, index)}
                    disabled={busy}
                  >
                    <IconSave /> Save Outfit
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <hr className="section-divider" />

        {/* ── Closet & Outfits ── */}
        <div className="two-col-grid">
          {/* Closet */}
          <div>
            <div className="section-header">
              <div>
                <h2 className="section-title">My Closet</h2>
                <p className="section-subtitle">{clothingItems.length} item{clothingItems.length === 1 ? "" : "s"}</p>
              </div>
            </div>

            <div className="card">
              {clothingItems.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">👗</div>
                  <p className="empty-state-text">Your closet is empty. Analyze images and add items!</p>
                </div>
              ) : (
                <div className="column">
                  {clothingItems.map((item) => (
                    <div className="closet-item" key={item.id}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        className="closet-item-thumb"
                        src={getImageUrl(item.image_id, token)}
                        alt={item.clothing_type}
                        loading="lazy"
                      />
                      <div className="closet-item-info">
                        <div className="closet-item-type">{item.clothing_type}</div>
                        <div className="closet-item-id">Image #{item.image_id}</div>
                      </div>
                      <span className="badge badge-neutral">#{item.id}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Saved Outfits */}
          <div>
            <div className="section-header">
              <div>
                <h2 className="section-title">Saved Outfits</h2>
                <p className="section-subtitle">{outfits.length} outfit{outfits.length === 1 ? "" : "s"}</p>
              </div>
            </div>

            <div className="card">
              {outfits.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">💎</div>
                  <p className="empty-state-text">No saved outfits yet. Generate recommendations and save your favorites!</p>
                </div>
              ) : (
                <div className="column">
                  {outfits.map((outfit) => (
                    <div className="outfit-card" key={outfit.id}>
                      <div className="outfit-header">
                        <div className="outfit-name">{outfit.name}</div>
                        <span className="reco-score">
                          <IconStar />
                          {(outfit.compatibility_score ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <p className="outfit-items-list">Items: {outfit.items.join(", ")}</p>
                      <button
                        type="button"
                        className="btn-danger btn-sm"
                        onClick={() => handleDeleteOutfit(outfit.id)}
                        disabled={busy}
                      >
                        <IconTrash /> Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
