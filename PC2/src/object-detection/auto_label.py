"""
=============================================================
  UNSUPERVISED IMAGE LEARNING — NO LABELS NEEDED
  FYP: Autonomous Drone Navigation
=============================================================
  WHAT IT DOES:
    - Reads ALL your raw images from Google Drive (no labels)
    - Extracts deep features using pretrained ResNet50
    - Reduces dimensions with PCA
    - Clusters images into 5 groups automatically (K-Means)
    - Visualises clusters with UMAP
    - Saves cluster model + feature extractor to Drive

  WHY UNSUPERVISED:
    - You have too many images to label manually
    - The model discovers natural groupings on its own
    - Groups will likely separate: trees, buildings,
      animals, open sky, ground — without you telling it

  HOW TO RUN (Google Colab):
    1. Runtime > Change runtime type > T4 GPU (faster)
    2. Mount Google Drive
    3. Run: python train_unsupervised.py

  GOOGLE DRIVE STRUCTURE NEEDED:
    MyDrive/fyp_drone/
    └── images/                  ← just dump ALL images here
        ├── img001.jpg            ← no subfolders needed
        ├── img002.jpg
        ├── img003.png
        └── ...

  OUTPUT (saved to Drive):
    trained_models/unsupervised/
    ├── features.npy              ← extracted feature vectors
    ├── cluster_labels.npy        ← which cluster each image belongs to
    ├── cluster_model.pkl         ← K-Means model (for new images)
    ├── pca_model.pkl             ← PCA reducer
    ├── cluster_samples/          ← sample images per cluster
    │   ├── cluster_0/
    │   ├── cluster_1/
    │   └── ...
    └── results_summary.txt       ← cluster statistics
=============================================================
"""

import os
import shutil
import pickle
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import torch
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader

from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

DRIVE_ROOT  = '/content/drive/MyDrive/fyp_drone'
IMAGES_DIR  = os.path.join(DRIVE_ROOT, 'images')
OUTPUT_DIR  = os.path.join(DRIVE_ROOT, 'trained_models', 'unsupervised')

N_CLUSTERS     = 5       # number of groups to find
                          # (try 5 = tree, building, animal, sky, ground)
N_COMPONENTS   = 128     # PCA dimensions (keep 128 from 2048 ResNet features)
BATCH_SIZE     = 32      # images per batch (reduce to 16 if memory error)
N_SAMPLES_SHOW = 8       # sample images to show per cluster
IMAGE_SIZE     = 224     # ResNet expects 224x224


# ─────────────────────────────────────────────────────────────
# STEP 1 — LOAD ALL IMAGES (no labels, just file paths)
# ─────────────────────────────────────────────────────────────

class UnlabelledImageDataset(Dataset):
    """
    Loads all images from a folder — NO labels, NO subfolders needed.
    Just point it at a flat folder of .jpg/.png files.
    """

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}

    def __init__(self, folder, transform=None):
        self.transform = transform
        self.paths = []

        # Recursively find every image file
        for root, _, files in os.walk(folder):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext in self.EXTENSIONS:
                    self.paths.append(os.path.join(root, fname))

        print(f"[DATA] Found {len(self.paths):,} images in {folder}")
        if len(self.paths) == 0:
            raise FileNotFoundError(
                f"No images found in {folder}\n"
                f"Make sure your images are in: {IMAGES_DIR}"
            )

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        try:
            img = Image.open(path).convert('RGB')
        except Exception:
            # Return blank image if file is corrupted
            img = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), color=0)

        if self.transform:
            img = self.transform(img)
        return img, path   # return path so we can track which image → which cluster


def get_transform():
    """Standard ResNet preprocessing — normalise to ImageNet stats."""
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],   # ImageNet mean
            std =[0.229, 0.224, 0.225],   # ImageNet std
        ),
    ])


# ─────────────────────────────────────────────────────────────
# STEP 2 — EXTRACT DEEP FEATURES (ResNet50, pretrained)
# ─────────────────────────────────────────────────────────────

def build_feature_extractor():
    """
    Load pretrained ResNet50 and strip the final classification layer.

    ResNet50 normally outputs 1000 class probabilities.
    We remove the last layer → get 2048-dim feature vector instead.
    These features capture rich visual patterns without any training.

    WHY ResNet50?
    - Pretrained on 1.2M ImageNet images
    - Already understands textures, edges, shapes
    - Much better features than raw pixels for clustering
    - Free — no training needed
    """
    print("[FEATURES] Loading pretrained ResNet50...")
    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)

    # Remove the final fully-connected layer
    # model.fc was: Linear(2048 → 1000 classes)
    # We replace it with Identity → output is 2048-dim vector
    model.fc = torch.nn.Identity()
    model.eval()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model  = model.to(device)
    print(f"[FEATURES] Using device: {device}")
    return model, device


def extract_features(model, device, dataset):
    """
    Pass every image through ResNet50 and collect 2048-dim feature vectors.

    Args:
        model   : pretrained ResNet50 (last layer removed)
        device  : 'cuda' or 'cpu'
        dataset : UnlabelledImageDataset

    Returns:
        features (np.ndarray): shape (N_images, 2048)
        paths    (list)      : file path for each image
    """
    print(f"\n[FEATURES] Extracting features from {len(dataset):,} images...")
    print( "[FEATURES] This may take a few minutes...")

    loader = DataLoader(
        dataset,
        batch_size  = BATCH_SIZE,
        shuffle     = False,
        num_workers = 2,
        pin_memory  = (device == 'cuda'),
    )

    all_features = []
    all_paths    = []
    total_batches = len(loader)

    with torch.no_grad():
        for batch_idx, (images, paths) in enumerate(loader):
            images   = images.to(device)
            features = model(images)                        # (B, 2048)
            features = features.squeeze()                   # handle batch=1
            if features.ndim == 1:
                features = features.unsqueeze(0)

            all_features.append(features.cpu().numpy())
            all_paths.extend(paths)

            if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
                done = (batch_idx + 1) / total_batches * 100
                print(f"  Batch {batch_idx+1:4d}/{total_batches}  "
                      f"[{'█' * int(done//5):<20s}]  {done:.0f}%")

    features_array = np.vstack(all_features)
    print(f"\n[FEATURES] Done! Feature matrix: {features_array.shape}")
    return features_array, all_paths


# ─────────────────────────────────────────────────────────────
# STEP 3 — REDUCE DIMENSIONS WITH PCA
# ─────────────────────────────────────────────────────────────

def reduce_dimensions(features, n_components=N_COMPONENTS):
    """
    Reduce 2048-dim features → n_components dims using PCA.

    WHY PCA?
    - 2048 dimensions is too many for K-Means (curse of dimensionality)
    - PCA keeps the most important variation
    - 128 components typically keeps 85–95% of variance
    - Also removes noise from the feature space

    Returns:
        features_reduced : (N, n_components)
        pca              : fitted PCA object (save for inference)
        scaler           : fitted StandardScaler
    """
    print(f"\n[PCA] Reducing {features.shape[1]} → {n_components} dimensions...")

    # Standardise first (zero mean, unit variance)
    scaler   = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # PCA
    n_components = min(n_components, features.shape[0], features.shape[1])
    pca      = PCA(n_components=n_components, random_state=42)
    features_reduced = pca.fit_transform(features_scaled)

    variance_kept = pca.explained_variance_ratio_.sum() * 100
    print(f"[PCA] Variance retained: {variance_kept:.1f}%")
    print(f"[PCA] Reduced shape: {features_reduced.shape}")

    return features_reduced, pca, scaler


# ─────────────────────────────────────────────────────────────
# STEP 4 — FIND BEST NUMBER OF CLUSTERS (optional)
# ─────────────────────────────────────────────────────────────

def find_best_k(features_reduced, k_range=range(2, 11)):
    """
    Run K-Means for different K values and plot silhouette scores.
    Higher silhouette score → better cluster separation.

    Run this BEFORE train_clusters() if you're unsure how many
    natural groups exist in your images.
    """
    print("\n[K-SEARCH] Searching for best number of clusters...")
    scores   = []
    inertias = []

    for k in k_range:
        km = MiniBatchKMeans(n_clusters=k, random_state=42,
                             n_init=3, batch_size=1024)
        labels  = km.fit_predict(features_reduced)
        sil     = silhouette_score(features_reduced, labels,
                                   sample_size=min(5000, len(labels)))
        inertia = km.inertia_
        scores.append(sil)
        inertias.append(inertia)
        print(f"  K={k:2d}  Silhouette: {sil:.4f}  Inertia: {inertia:.0f}")

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(list(k_range), scores, 'b-o', markersize=8)
    ax1.axvline(x=N_CLUSTERS, color='red', linestyle='--',
                label=f'Your choice K={N_CLUSTERS}')
    ax1.set_title('Silhouette Score (higher = better)')
    ax1.set_xlabel('Number of clusters K')
    ax1.set_ylabel('Silhouette Score')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(list(k_range), inertias, 'r-s', markersize=8)
    ax2.axvline(x=N_CLUSTERS, color='blue', linestyle='--',
                label=f'Your choice K={N_CLUSTERS}')
    ax2.set_title('Inertia / Elbow Method (look for elbow)')
    ax2.set_xlabel('Number of clusters K')
    ax2.set_ylabel('Inertia (lower = tighter clusters)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.suptitle('Choosing the Right Number of Clusters', fontsize=14)
    plt.tight_layout()

    plot_path = os.path.join(OUTPUT_DIR, 'k_selection.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"[K-SEARCH] Plot saved → {plot_path}")

    best_k = list(k_range)[np.argmax(scores)]
    print(f"[K-SEARCH] Best K by silhouette: {best_k}")
    return best_k


# ─────────────────────────────────────────────────────────────
# STEP 5 — CLUSTER WITH K-MEANS
# ─────────────────────────────────────────────────────────────

def train_clusters(features_reduced, n_clusters=N_CLUSTERS):
    """
    Cluster all images into n_clusters groups using K-Means.

    MiniBatchKMeans is used instead of standard KMeans because:
    - Works on large datasets (10,000+ images) without memory issues
    - Much faster (processes mini-batches instead of all data)
    - Almost identical quality to full K-Means

    Returns:
        labels      : (N,) array — cluster ID for each image
        kmeans      : fitted KMeans model (save for inference on new images)
        sil_score   : silhouette score of the clustering
    """
    print(f"\n[CLUSTER] Clustering {len(features_reduced):,} images "
          f"into {n_clusters} groups...")

    kmeans = MiniBatchKMeans(
        n_clusters  = n_clusters,
        random_state= 42,
        n_init      = 10,          # run 10 times, keep best
        batch_size  = 1024,
        max_iter    = 300,
        verbose     = 0,
    )

    labels = kmeans.fit_predict(features_reduced)

    # Silhouette score (sample 5000 to keep it fast)
    sil = silhouette_score(
        features_reduced, labels,
        sample_size=min(5000, len(labels)),
        random_state=42,
    )

    print(f"[CLUSTER] Silhouette Score: {sil:.4f}")
    print(f"          (0 = random, 1 = perfect separation)")
    print()

    # Cluster sizes
    unique, counts = np.unique(labels, return_counts=True)
    for cid, cnt in zip(unique, counts):
        bar = '█' * int(cnt / len(labels) * 40)
        pct = cnt / len(labels) * 100
        print(f"  Cluster {cid}: {cnt:5d} images ({pct:.1f}%)  {bar}")

    return labels, kmeans, sil


# ─────────────────────────────────────────────────────────────
# STEP 6 — VISUALISE WITH UMAP
# ─────────────────────────────────────────────────────────────

def visualise_clusters(features_reduced, labels, paths):
    """
    Use UMAP to project features into 2D and plot coloured by cluster.

    UMAP is better than PCA for visualisation — it preserves
    local structure, so similar images appear near each other.
    """
    try:
        import umap
    except ImportError:
        print("[UMAP] Installing umap-learn...")
        os.system("pip install umap-learn -q")
        import umap

    print("\n[UMAP] Projecting to 2D for visualisation...")

    reducer   = umap.UMAP(n_components=2, random_state=42, verbose=False)
    embedding = reducer.fit_transform(features_reduced)

    fig, ax = plt.subplots(figsize=(12, 9))
    colors  = plt.cm.tab10(np.linspace(0, 1, N_CLUSTERS))

    for cid in range(N_CLUSTERS):
        mask = labels == cid
        ax.scatter(
            embedding[mask, 0],
            embedding[mask, 1],
            c      = [colors[cid]],
            label  = f'Cluster {cid} ({mask.sum()} imgs)',
            alpha  = 0.5,
            s      = 5,
        )

    ax.set_title('UMAP Projection — Each dot is one image\n'
                 'Similar images cluster together', fontsize=14)
    ax.legend(markerscale=4, fontsize=11)
    ax.set_xlabel('UMAP Dimension 1')
    ax.set_ylabel('UMAP Dimension 2')
    ax.grid(True, alpha=0.2)

    plot_path = os.path.join(OUTPUT_DIR, 'umap_clusters.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"[UMAP] Plot saved → {plot_path}")


# ─────────────────────────────────────────────────────────────
# STEP 7 — SAVE SAMPLE IMAGES PER CLUSTER
# ─────────────────────────────────────────────────────────────

def save_cluster_samples(labels, paths, n_samples=N_SAMPLES_SHOW):
    """
    Copy N sample images from each cluster to a folder so you can
    inspect what each cluster actually contains visually.

    After running this, open Drive and look at cluster_samples/:
    - Cluster 0 might be all trees
    - Cluster 1 might be buildings
    - Cluster 2 might be animals
    → You can then name each cluster manually
    """
    print(f"\n[SAMPLES] Saving {n_samples} sample images per cluster...")

    samples_root = os.path.join(OUTPUT_DIR, 'cluster_samples')
    # Clear old samples
    if os.path.exists(samples_root):
        shutil.rmtree(samples_root)

    for cid in range(N_CLUSTERS):
        cluster_dir = os.path.join(samples_root, f'cluster_{cid}')
        os.makedirs(cluster_dir, exist_ok=True)

        cluster_paths = [paths[i] for i, lbl in enumerate(labels) if lbl == cid]
        samples = cluster_paths[:n_samples]

        for src in samples:
            fname = os.path.basename(src)
            dst   = os.path.join(cluster_dir, fname)
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass

        print(f"  Cluster {cid}: saved {len(samples)} samples → {cluster_dir}")

    # Also create a visual grid
    _create_cluster_grid(labels, paths, samples_root, n_samples)


def _create_cluster_grid(labels, paths, samples_root, n_samples):
    """Create a single image grid showing samples from every cluster."""
    fig = plt.figure(figsize=(n_samples * 2, N_CLUSTERS * 2.5))
    gs  = gridspec.GridSpec(N_CLUSTERS, n_samples,
                            hspace=0.4, wspace=0.1)

    colors = plt.cm.tab10(np.linspace(0, 1, N_CLUSTERS))

    for cid in range(N_CLUSTERS):
        cluster_paths = [paths[i] for i, lbl in enumerate(labels) if lbl == cid]
        samples = cluster_paths[:n_samples]

        for j, path in enumerate(samples):
            ax = fig.add_subplot(gs[cid, j])
            try:
                img = Image.open(path).convert('RGB')
                img = img.resize((128, 128))
                ax.imshow(img)
            except Exception:
                ax.set_facecolor('gray')

            ax.axis('off')
            if j == 0:
                ax.set_ylabel(
                    f'Cluster {cid}',
                    rotation=0, labelpad=55,
                    va='center', fontsize=11,
                    color=colors[cid],
                )

    plt.suptitle('Sample Images per Cluster\n'
                 '(look at each row to understand what the cluster represents)',
                 fontsize=13, y=1.01)

    grid_path = os.path.join(samples_root, 'cluster_grid.png')
    plt.savefig(grid_path, dpi=120, bbox_inches='tight')
    plt.show()
    print(f"[SAMPLES] Grid saved → {grid_path}")


# ─────────────────────────────────────────────────────────────
# STEP 8 — SAVE MODELS & RESULTS
# ─────────────────────────────────────────────────────────────

def save_all(features, features_reduced, labels, paths,
             kmeans, pca, scaler, sil_score):
    """Save everything to Google Drive for later use."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Numpy arrays
    np.save(os.path.join(OUTPUT_DIR, 'features.npy'),        features)
    np.save(os.path.join(OUTPUT_DIR, 'features_reduced.npy'), features_reduced)
    np.save(os.path.join(OUTPUT_DIR, 'cluster_labels.npy'),   labels)

    # Image paths mapped to cluster IDs
    path_label_map = {p: int(l) for p, l in zip(paths, labels)}
    import json
    with open(os.path.join(OUTPUT_DIR, 'image_clusters.json'), 'w') as f:
        json.dump(path_label_map, f, indent=2)

    # Sklearn models
    with open(os.path.join(OUTPUT_DIR, 'cluster_model.pkl'), 'wb') as f:
        pickle.dump(kmeans, f)
    with open(os.path.join(OUTPUT_DIR, 'pca_model.pkl'), 'wb') as f:
        pickle.dump(pca, f)
    with open(os.path.join(OUTPUT_DIR, 'scaler.pkl'), 'wb') as f:
        pickle.dump(scaler, f)

    # Human-readable summary
    unique, counts = np.unique(labels, return_counts=True)
    summary_lines = [
        "UNSUPERVISED CLUSTERING RESULTS",
        "=" * 40,
        f"Total images      : {len(labels):,}",
        f"Number of clusters: {N_CLUSTERS}",
        f"PCA components    : {N_COMPONENTS}",
        f"Silhouette score  : {sil_score:.4f}",
        "",
        "Cluster sizes:",
    ]
    for cid, cnt in zip(unique, counts):
        summary_lines.append(
            f"  Cluster {cid}: {cnt:5d} images ({cnt/len(labels)*100:.1f}%)"
        )
    summary_lines += [
        "",
        "Next steps:",
        "  1. Open cluster_samples/ in Drive",
        "  2. Look at each cluster's images",
        "  3. Name each cluster (tree, building, etc.)",
        "  4. Use cluster_model.pkl to classify new images",
    ]

    summary_path = os.path.join(OUTPUT_DIR, 'results_summary.txt')
    with open(summary_path, 'w') as f:
        f.write('\n'.join(summary_lines))

    print(f"\n[SAVE] All files saved to: {OUTPUT_DIR}")
    for fname in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, fname)
        if os.path.isfile(fpath):
            size_mb = os.path.getsize(fpath) / 1e6
            print(f"  {fname:<35s}  {size_mb:.2f} MB")


# ─────────────────────────────────────────────────────────────
# STEP 9 — INFERENCE: CLASSIFY A NEW IMAGE (no label needed)
# ─────────────────────────────────────────────────────────────

def classify_new_image(image_path, model, device,
                       kmeans, pca, scaler,
                       cluster_names=None):
    """
    Assign a NEW unseen image to one of the learned clusters.

    Used in your object_detection microservice to classify
    what the drone's camera sees WITHOUT needing labels.

    Args:
        image_path    : path to image file (or numpy BGR frame from OpenCV)
        model         : pretrained ResNet50 (feature extractor)
        device        : 'cuda' or 'cpu'
        kmeans        : loaded cluster_model.pkl
        pca           : loaded pca_model.pkl
        scaler        : loaded scaler.pkl
        cluster_names : optional dict {0: 'tree', 1: 'building', ...}
                        assign after inspecting cluster_samples/

    Returns:
        dict with cluster_id, cluster_name, distances to all centroids
    """
    transform = get_transform()

    # Load image
    if isinstance(image_path, str):
        img = Image.open(image_path).convert('RGB')
    else:
        # OpenCV frame (numpy array BGR)
        import cv2
        img = Image.fromarray(cv2.cvtColor(image_path, cv2.COLOR_BGR2RGB))

    img_tensor = transform(img).unsqueeze(0).to(device)

    # Extract features
    model.eval()
    with torch.no_grad():
        features = model(img_tensor).squeeze().cpu().numpy()  # (2048,)

    # Reduce dimensions (same pipeline as training)
    features_scaled   = scaler.transform(features.reshape(1, -1))
    features_reduced  = pca.transform(features_scaled)

    # Predict cluster
    cluster_id  = int(kmeans.predict(features_reduced)[0])

    # Distance to each centroid (confidence proxy)
    distances   = np.linalg.norm(
        features_reduced - kmeans.cluster_centers_, axis=1
    ).tolist()

    name = cluster_names.get(cluster_id, f'cluster_{cluster_id}') \
           if cluster_names else f'cluster_{cluster_id}'

    return {
        "cluster_id"  : cluster_id,
        "cluster_name": name,
        "distances"   : {f"cluster_{i}": round(d, 4)
                         for i, d in enumerate(distances)},
        "confidence"  : round(1.0 - distances[cluster_id] /
                              (sum(distances) + 1e-9), 4),
    }


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  UNSUPERVISED IMAGE LEARNING — NO LABELS NEEDED")
    print("=" * 55)
    print(f"  Images folder : {IMAGES_DIR}")
    print(f"  Output folder : {OUTPUT_DIR}")
    print(f"  N clusters    : {N_CLUSTERS}")
    print(f"  PCA dims      : {N_COMPONENTS}")
    print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Load all images (no labels)
    dataset   = UnlabelledImageDataset(IMAGES_DIR, transform=get_transform())

    # 2. Build feature extractor (pretrained ResNet50, no training)
    model, device = build_feature_extractor()

    # 3. Extract 2048-dim features from every image
    features, paths = extract_features(model, device, dataset)

    # Save raw features immediately (expensive step — don't redo it)
    np.save(os.path.join(OUTPUT_DIR, 'features.npy'),     features)
    np.save(os.path.join(OUTPUT_DIR, 'image_paths.npy'),  np.array(paths))
    print(f"\n[SAVE] Raw features saved (so you don't re-extract if Colab disconnects)")

    # 4. Reduce dimensions
    features_reduced, pca, scaler = reduce_dimensions(features, N_COMPONENTS)

    # 5. (Optional) Find best K — uncomment to run
    # best_k = find_best_k(features_reduced, k_range=range(2, 11))
    # Then set N_CLUSTERS = best_k above and re-run from Step 5

    # 6. Cluster
    labels, kmeans, sil_score = train_clusters(features_reduced, N_CLUSTERS)

    # 7. Visualise with UMAP
    visualise_clusters(features_reduced, labels, paths)

    # 8. Save sample images per cluster (inspect in Drive)
    save_cluster_samples(labels, paths, n_samples=N_SAMPLES_SHOW)

    # 9. Save all models and results
    save_all(features, features_reduced, labels, paths,
             kmeans, pca, scaler, sil_score)

    print("\n\n✓ UNSUPERVISED TRAINING COMPLETE — NO LABELS NEEDED")
    print(f"\n  Open this in your Drive to see results:")
    print(f"  {OUTPUT_DIR}/cluster_samples/cluster_grid.png")
    print()
    print("  NEXT STEPS:")
    print("  1. Open cluster_samples/ in Drive")
    print("  2. Look at each cluster row in cluster_grid.png")
    print("     → Rename clusters: {0: 'tree', 1: 'building', ...}")
    print("  3. Use classify_new_image() in your microservice")
    print("     to classify live camera frames without labels")
    print()
    print("  TO LOAD MODELS LATER:")
    print("    import pickle, numpy as np")
    print(f"    kmeans = pickle.load(open('{OUTPUT_DIR}/cluster_model.pkl','rb'))")
    print(f"    pca    = pickle.load(open('{OUTPUT_DIR}/pca_model.pkl','rb'))")
    print(f"    scaler = pickle.load(open('{OUTPUT_DIR}/scaler.pkl','rb'))")