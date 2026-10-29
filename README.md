# 🔬 StainShift: Histopathology Stain Domain Shift AI Application & Benchmark

> **Scientific Scope:** *Physics-informed histopathology stain normalization and robustness benchmark for colorectal cancer classification.*
>
> ⚠️ **Non-Clinical Research Disclaimer:** StainShift is an exploratory research engineering prototype. It is **not** a certified medical device, diagnostic system, or clinical decision support software. Softmax probability outputs represent model scoring distributions across 9 research classes and must never be interpreted as clinical diagnoses or medical advice.

---

## 1. Application Overview

StainShift is a full-stack, user-facing biomedical AI application that accepts uploaded histopathology image patches, simulates physical Hematoxylin and Eosin (H&E) stain variations in Beer-Lambert optical density space, and executes real model inference using pre-trained PyTorch neural networks.

### Core Capabilities
1. **Interactive AI Workspace**: Drag-and-drop support for single patches, multiple image files, and whole dataset ZIP archives (`.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.zip`).
2. **Real Model Inference**: Powered directly by verified PyTorch checkpoints (`MobileNetV3-Small`) trained on the CRC-VAL-HE-7K benchmark.
3. **Dual Model Modes**:
   - **Baseline Model**: Trained with standard empirical risk minimization and geometric augmentations (collapses under stain shift).
   - **Stain-Robust Model**: Trained with physics-based Macenko Beer-Lambert dye perturbation augmentation (maintains high accuracy across shifts).
   - **Side-by-Side Comparison**: Concurrently runs both models on the identical shifted image and automatically detects prediction flips.
4. **Physics-Informed Stain Variations**:
   - `original`: Native unperturbed patch.
   - `reconstruction_only`: Macenko deconvolution control (inversion loss baseline).
   - `heavy_hematoxylin`: Dark hyperchromatic nuclei bias ($\alpha_H = 1.65, \alpha_E = 0.85$).
   - `heavy_eosin`: Vivid pink cytoplasm and stroma dominance ($\alpha_H = 0.75, \alpha_E = 1.65$).
   - `pale_understained`: Weak optical density and low dye absorption.
   - `dark_overstained`: High global dye absorption.
   - `synthetic_warm_shift` & `synthetic_cool_shift`: Complex optical rotations ($\pm 8^\circ$).
5. **Interactive Intensity Slider**: Continuous perturbation scaling from $0.0\text{x}$ to $2.0\text{x}$ ($1.0\text{x}$ corresponds to calibrated benchmark profiles).
6. **9-Class Probability Distributions**: Full softmax breakdowns across ADI, BACK, DEB, LYM, MUC, MUS, NORM, STR, and TUM.
7. **Batch Predictions & CSV Export**: Download RFC-4180 compliant CSV reports containing predictions, confidence scores, probability vectors, and hardware latency.

---

## 2. Architecture & Deployment Strategy

```
                          ┌─────────────────────────────────────────────────────┐
                          │                 Client Web Browser                  │
                          │   (Next.js 14 App Router, Tailwind CSS, Lucide)     │
                          └──────────┬───────────────────────────────▲──────────┘
                                     │                               │
                      POST /predict  │ Multipart Form                │ Base64 Previews
                      GET /health    │ (Images / ZIP)                │ Softmax Probabilities
                                     ▼                               │
                          ┌──────────────────────────────────────────┴──────────┐
                          │               FastAPI Inference API                 │
                          │        (Python 3.11+, PyTorch 2.6, PIL)             │
                          ├─────────────────────────────────────────────────────┤
                          │  • Content-based Image Validation (RGB/RGBA 8-bit)  │
                          │  • Zip-Slip & Zip-Bomb Memory Protection            │
                          │  • Macenko Beer-Lambert Optical Density Decomposer  │
                          │  • MobileNetV3-Small Checkpoints (baseline, robust) │
                          │  • Hardware Accelerator Synchronization (MPS/CPU)   │
                          └─────────────────────────────────────────────────────┘
```

### Production Architecture
- **Frontend**: Next.js static export (`output: 'export'`) hosted with infinite scalability and zero cold-starts on **Vercel**.
- **Backend**: FastAPI Python service running in a containerized environment (Render, Railway, Fly.io, or AWS/GCP) where PyTorch (850+ MB) and trained checkpoints are natively supported.
- **Frontend-to-Backend Connection**: HTTPS REST API with configurable `NEXT_PUBLIC_API_URL` and CORS protection.

---

## 3. Directory Structure

```
stainshift/
├── api/                                # FastAPI inference backend
│   ├── __init__.py
│   ├── main.py                         # REST API endpoints & CORS configuration
│   ├── inference.py                    # PyTorch model loader, transforms, and ZIP parser
│   └── schemas.py                      # Pydantic request/response data contracts
├── website/                            # Next.js 14 Frontend Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                # Interactive AI Workspace (Primary Landing)
│   │   │   ├── dashboard/page.tsx      # Verified Stage B Benchmark Dashboard
│   │   │   ├── demo/page.tsx           # Precomputed 72-Patch Option B Explorer
│   │   │   ├── methodology/page.tsx    # Optical density physics & SVD math
│   │   │   ├── limitations/page.tsx    # Scientific caveats & single-cohort bounds
│   │   │   └── reproduction/page.tsx   # Environment configs & CLI commands
│   │   ├── components/workspace/       # Uploader, ModelSelector, StainControls, Tables
│   │   ├── components/charts/          # Accessible SVG charts with HTML table alternatives
│   │   └── lib/types.ts                # TypeScript data interfaces
│   ├── public/                         # Public static results and demo patches
│   ├── package.json
│   └── next.config.mjs                 # Static export configuration
├── models/full_benchmark_20261029_1838/
│   ├── baseline.pth                    # Authoritative baseline model checkpoint
│   └── robust_stain_aug.pth            # Authoritative stain-robust model checkpoint
├── data/CRC-VAL-HE-7K/                 # Local 7,180-patch dataset (DACHS cohort)
├── src/                                # Core scientific library
│   ├── dataset.py                      # Image loaders, Pillow transforms, and split logic
│   ├── models.py                       # Neural network architectures & checkpoint I/O
│   └── stain_shift.py                  # Macenko deconvolution & Reinhard color transfer
├── tests/                              # Comprehensive test suite (74 tests)
│   ├── test_api.py                     # API contracts, file parsing, and parity tests
│   └── ...                             # Mathematical and benchmark regression tests
├── Dockerfile                          # Container specification for Python inference API
├── Procfile                            # PaaS process file (Render / Railway)
├── requirements.txt                    # Pinned runtime dependencies
└── vercel.json                         # Vercel deployment specification
```

---

## 4. Local Development Quickstart

### Prerequisites
- Python 3.10+ (with `.venv` activated)
- Node.js 18+ and npm

### 1. Launch the FastAPI Backend
```bash
# From repository root
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
Verify the backend is live:
```bash
curl http://127.0.0.1:8000/health
```

### 2. Launch the Next.js Frontend
```bash
cd website
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser. The backend indicator will illuminate green: **AI Models Ready (MPS/CPU)**.

---

## 5. API Reference

### `GET /health`
Returns backend status, active compute device (`mps`, `cuda`, `cpu`), and loaded models.
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "device": "mps",
  "models_available": {
    "baseline": true,
    "robust_stain_aug": true
  },
  "supported_formats": [".jpeg", ".jpg", ".png", ".tif", ".tiff", ".zip"],
  "supported_conditions": ["original", "reconstruction_only", "heavy_hematoxylin", "heavy_eosin", "pale_understained", "dark_overstained", "synthetic_warm_shift", "synthetic_cool_shift"]
}
```

### `POST /predict`
Executes physics-based stain shift and model inference.
- **Form Parameters**:
  - `files`: One or more image files or a `.zip` archive.
  - `model_id`: `"robust_stain_aug"` (default), `"baseline"`, or `"compare"`.
  - `condition`: Desired stain profile (default `"original"`).
  - `intensity`: Float from $0.0$ to $2.0$ (default $1.0$).
- **Response**:
  - `summary`: Aggregate metrics, success/failure counts, class distribution, and average latency.
  - `results`: Array of per-image predictions, base64 thumbnails, 9-class probabilities, and comparison agreement flags.

---

## 6. Testing & Mathematical Verification

Run the full test suite (74 tests):
```bash
pytest -v
```

### Parity Guarantee
Every model output produced by `POST /predict` is mathematically identical to a direct PyTorch `model(transform(img))` forward pass:
- Probability vectors sum to $1.0000 \pm 10^{-4}$.
- Predicted class matches $\operatorname{argmax}(p)$.
- Confidence strictly equals $\max(p)$.

---

## 7. Deployment Instructions

### Frontend on Vercel
1. Link the repository to your Vercel account.
2. Set Root Directory to `website` (or use the root `vercel.json`).
3. Configure the environment variable:
   - `NEXT_PUBLIC_API_URL`: URL of your deployed FastAPI backend (e.g., `https://stainshift-api.onrender.com`).
4. Deploy!

### Backend on Render / Railway / Fly.io / Docker
Deploy using the provided `Dockerfile`:
```bash
docker build -t stainshift-api .
docker run -p 8000:8000 stainshift-api
```

---

## 8. Privacy, Security & Data Handling
- **Zero Persistent Storage**: Uploaded image bytes are processed directly in-memory via `io.BytesIO`. No uploaded patient or user images are written to disk.
- **Zip-Slip & Zip-Bomb Protection**: Strict path sanitization and uncompressed size bounds ($100\text{ MB}$ max).
- **Metadata Stripping**: Previews and returned thumbnails strip all EXIF, instrument, and proprietary hospital headers.
- **CORS Configurable**: Restrict API access to trusted frontend origins via `ALLOW_ORIGINS`.
