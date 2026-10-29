"""
StainShift: Physics-based Stain Deconvolution, Perturbation, and Normalization
Implements Beer-Lambert optical density deconvolution (Macenko et al.) and
Reinhard Ruderman l-alpha-beta color transfer for digital histopathology.
100% pure NumPy / PIL - no OpenCV dependency required.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# Specific, scientifically meaningful exceptions for numerical transformation failures
class StainDecompositionError(RuntimeError):
    """Base exception for stain decomposition or deconvolution failures."""
    pass


class InsufficientTissueError(StainDecompositionError):
    """Raised when an image lacks enough optical-density-filtered tissue pixels."""
    pass


class DegenerateTissueError(StainDecompositionError):
    """Raised when optical density covariance is degenerate or stain vectors cannot be separated."""
    pass


class MacenkoStainDecomposer:
    """
    Decomposes an H&E RGB image into Hematoxylin and Eosin stain vectors and concentrations
    using the Macenko method (optical density PCA).
    """

    # Standard canonical H&E optical density vectors from Macenko et al. 2009
    CANONICAL_HE = np.array([
        [0.644211, 0.716556, 0.266844],  # Hematoxylin canonical OD
        [0.092783, 0.954111, 0.283111]   # Eosin canonical OD
    ], dtype=np.float64)

    def __init__(self, alpha: float = 1.0, beta: float = 0.15, min_tissue_pixels: int = 100):
        self.alpha = float(alpha)  # percentile for robust angle estimation (e.g., 1st and 99th)
        self.beta = float(beta)    # optical density threshold to discard background glass
        self.min_tissue_pixels = int(min_tissue_pixels)

    def rgb_to_od(self, img_rgb: np.ndarray) -> np.ndarray:
        """Converts RGB image [0, 255] to Optical Density (OD) space via Beer-Lambert."""
        img = img_rgb.astype(np.float64)
        # Avoid log(0) and clamp within physically plausible range [1.0, 255.0]
        img = np.clip(img, 1.0, 255.0)
        od = -np.log10(img / 255.0)
        return od

    def od_to_rgb(self, od: np.ndarray) -> np.ndarray:
        """Converts Optical Density back to RGB image [0, 255]."""
        if not np.all(np.isfinite(od)):
            raise StainDecompositionError("Non-finite values encountered in optical density array.")
        img = 255.0 * np.power(10.0, -od)
        img = np.clip(img, 0.0, 255.0).astype(np.uint8)
        return img

    def extract_stain_vectors_and_concentrations(
        self,
        img_rgb: np.ndarray,
        allow_fallback: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int]]:
        """
        Calculates the 2x3 stain matrix (Hematoxylin and Eosin vectors)
        and the (H*W, 2) concentration map for the image.
        """
        if img_rgb.ndim != 3 or img_rgb.shape[2] != 3:
            raise ValueError(f"Expected RGB image array of shape (H, W, 3), got {img_rgb.shape}")

        od = self.rgb_to_od(img_rgb)
        h, w, c = od.shape
        od_flat = od.reshape((-1, 3))

        # Filter out optical density below beta (transparent glass/background)
        mask = np.all(od_flat > self.beta, axis=1)
        od_filtered = od_flat[mask]

        if len(od_filtered) < self.min_tissue_pixels:
            if not allow_fallback:
                raise InsufficientTissueError(
                    f"Only {len(od_filtered)} pixels above optical density threshold beta={self.beta} "
                    f"(minimum required: {self.min_tissue_pixels}). Cannot reliably estimate stain vectors."
                )
            # Fallback to standard canonical H&E vectors for background/glass patches
            he_matrix = self.CANONICAL_HE.copy()
            he_matrix /= np.linalg.norm(he_matrix, axis=1, keepdims=True)
            concentrations = np.linalg.lstsq(he_matrix.T, od_flat.T, rcond=None)[0].T
            concentrations = np.maximum(concentrations, 0.0)
            return he_matrix, concentrations, (h, w)

        # 1. Covariance matrix of filtered OD values
        cov = np.cov(od_filtered, rowvar=False)
        if not np.all(np.isfinite(cov)):
            raise DegenerateTissueError("OD covariance matrix contains non-finite values.")

        # 2. Eigenvectors of covariance matrix
        eigvals, eigvecs = np.linalg.eigh(cov)

        # Check for degenerate covariance (e.g. constant/uniform patch where variance is ~0)
        if eigvals[-1] < 1e-7:
            if not allow_fallback:
                raise DegenerateTissueError("OD covariance matrix has near-zero variance; stain vectors cannot be separated.")
            he_matrix = self.CANONICAL_HE.copy()
            he_matrix /= np.linalg.norm(he_matrix, axis=1, keepdims=True)
            concentrations = np.linalg.lstsq(he_matrix.T, od_flat.T, rcond=None)[0].T
            concentrations = np.maximum(concentrations, 0.0)
            return he_matrix, concentrations, (h, w)

        # Macenko 2D projection on top 2 eigenvectors
        top_eigvecs = eigvecs[:, [2, 1]]

        # 3. Project filtered OD values onto the 2D plane
        projected = np.dot(od_filtered, top_eigvecs)

        # 4. Compute angles on the 2D projection
        angles = np.arctan2(projected[:, 1], projected[:, 0])

        # 5. Find robust extreme angles (alpha and 100-alpha percentiles)
        min_angle = np.percentile(angles, self.alpha)
        max_angle = np.percentile(angles, 100.0 - self.alpha)

        # Check angular separation
        if abs(max_angle - min_angle) < 1e-4:
            if not allow_fallback:
                raise DegenerateTissueError("Insufficient angular spread between stain extremes in 2D OD space.")
            he_matrix = self.CANONICAL_HE.copy()
            he_matrix /= np.linalg.norm(he_matrix, axis=1, keepdims=True)
            concentrations = np.linalg.lstsq(he_matrix.T, od_flat.T, rcond=None)[0].T
            concentrations = np.maximum(concentrations, 0.0)
            return he_matrix, concentrations, (h, w)

        v_min = np.dot(top_eigvecs, np.array([np.cos(min_angle), np.sin(min_angle)]))
        v_max = np.dot(top_eigvecs, np.array([np.cos(max_angle), np.sin(max_angle)]))

        # Order: [Hematoxylin, Eosin]
        if v_min[0] > v_max[0]:
            stain_matrix = np.vstack([v_min, v_max])
        else:
            stain_matrix = np.vstack([v_max, v_min])

        # Check vector norms
        norms = np.linalg.norm(stain_matrix, axis=1, keepdims=True)
        if np.any(norms < 1e-6):
            raise StainDecompositionError("Extracted stain vectors have near-zero norm.")
        stain_matrix = stain_matrix / norms

        # 6. Solve for concentrations: OD = C * S  => C = OD * S^+
        concentrations = np.linalg.lstsq(stain_matrix.T, od_flat.T, rcond=None)[0].T
        if not np.all(np.isfinite(concentrations)):
            raise StainDecompositionError("Non-finite values encountered in concentration estimation.")
        concentrations = np.maximum(concentrations, 0.0)

        return stain_matrix, concentrations, (h, w)

    def reconstruct(self, img_rgb: np.ndarray) -> np.ndarray:
        """
        Decomposes and reconstructs the image without concentration or angular perturbation.
        Used as a reconstruction-only control condition to separate deconvolution artifacts
        from stain shift effects.
        """
        stain_matrix, concentrations, (h, w) = self.extract_stain_vectors_and_concentrations(img_rgb)
        od_reconstructed = np.dot(concentrations, stain_matrix).reshape((h, w, 3))
        return self.od_to_rgb(od_reconstructed)

    def perturb(
        self,
        img_rgb: np.ndarray,
        alpha_h: float = 1.0,
        alpha_e: float = 1.0,
        stain_rot_deg: float = 0.0,
        add_noise: float = 0.0
    ) -> np.ndarray:
        """
        Perturbs the image by scaling Hematoxylin concentration (alpha_h),
        scaling Eosin concentration (alpha_e), or rotating the stain vectors.

        CRITICAL INTEGRITY CONTRACT:
        When neutral parameters (alpha_h=1.0, alpha_e=1.0, stain_rot_deg=0.0, add_noise=0.0)
        are requested, returns an exact copy of img_rgb without deconvolution/reconstruction loss.
        """
        # Exact identity bypass for neutral controls
        is_neutral = (
            abs(alpha_h - 1.0) < 1e-6
            and abs(alpha_e - 1.0) < 1e-6
            and abs(stain_rot_deg) < 1e-4
            and abs(add_noise) < 1e-6
        )
        if is_neutral:
            return img_rgb.copy()

        stain_matrix, concentrations, (h, w) = self.extract_stain_vectors_and_concentrations(img_rgb)

        c_perturbed = concentrations.copy()
        c_perturbed[:, 0] *= alpha_h
        c_perturbed[:, 1] *= alpha_e

        s_perturbed = stain_matrix.copy()
        if abs(stain_rot_deg) > 1e-3:
            rad = np.radians(stain_rot_deg)
            rot_matrix = np.array([
                [np.cos(rad), -np.sin(rad), 0.0],
                [np.sin(rad),  np.cos(rad), 0.0],
                [0.0,          0.0,         1.0]
            ])
            s_perturbed = np.dot(s_perturbed, rot_matrix)
            s_perturbed = np.maximum(s_perturbed, 0.0)
            norms = np.linalg.norm(s_perturbed, axis=1, keepdims=True)
            if np.any(norms < 1e-6):
                raise StainDecompositionError("Rotated stain vectors have near-zero norm.")
            s_perturbed /= norms

        if add_noise > 0.0:
            noise = np.random.normal(0, add_noise, s_perturbed.shape)
            s_perturbed = np.maximum(s_perturbed + noise, 0.0)
            norms = np.linalg.norm(s_perturbed, axis=1, keepdims=True)
            if np.any(norms < 1e-6):
                raise StainDecompositionError("Perturbed stain vectors have near-zero norm after noise addition.")
            s_perturbed /= norms

        od_perturbed = np.dot(c_perturbed, s_perturbed)
        od_perturbed = od_perturbed.reshape((h, w, 3))

        return self.od_to_rgb(od_perturbed)


class ReinhardNormalizer:
    """
    Reinhard color transfer algorithm in Ruderman l-alpha-beta color space.
    Fully pure-numpy implementation (Reinhard et al. 2001).

    NOTE: Default target statistics are calibrated for digital H&E histology in
    Ruderman log10(LMS) space. Use fit(reference_image) for empirical calibration
    against a designated target scanner or laboratory reference image.
    """

    RGB_TO_LMS = np.array([
        [0.3811, 0.5783, 0.0402],
        [0.1967, 0.7244, 0.0782],
        [0.0241, 0.1288, 0.8444]
    ], dtype=np.float64)

    LMS_TO_LAB = np.array([
        [1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
        [1.0 / np.sqrt(6.0), 1.0 / np.sqrt(6.0), -2.0 / np.sqrt(6.0)],
        [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0), 0.0]
    ], dtype=np.float64)

    LAB_TO_LMS = np.linalg.inv(LMS_TO_LAB)
    LMS_TO_RGB = np.linalg.inv(RGB_TO_LMS)

    # Calibrated empirical reference statistics for H&E in log10 Ruderman space
    DEFAULT_HE_TARGET_MEANS = np.array([-0.40, -0.06, 0.02], dtype=np.float64)
    DEFAULT_HE_TARGET_STDS = np.array([0.25, 0.08, 0.02], dtype=np.float64)

    def __init__(
        self,
        target_means: Optional[np.ndarray] = None,
        target_stds: Optional[np.ndarray] = None
    ):
        if target_means is None:
            self.target_means = self.DEFAULT_HE_TARGET_MEANS.copy()
        else:
            self.target_means = np.asarray(target_means, dtype=np.float64)

        if target_stds is None:
            self.target_stds = self.DEFAULT_HE_TARGET_STDS.copy()
        else:
            self.target_stds = np.asarray(target_stds, dtype=np.float64)

    def fit(self, reference_img: np.ndarray) -> ReinhardNormalizer:
        """Fits target statistics directly from a designated reference H&E RGB patch."""
        lab = self._rgb_to_lab(reference_img)
        self.target_means = np.mean(lab, axis=0)
        self.target_stds = np.std(lab, axis=0) + 1e-6
        return self

    def _rgb_to_lab(self, img_rgb: np.ndarray) -> np.ndarray:
        flat = img_rgb.reshape((-1, 3)).astype(np.float64) / 255.0
        flat = np.clip(flat, 1e-6, 1.0)
        lms = np.dot(flat, self.RGB_TO_LMS.T)
        lms = np.maximum(lms, 1e-6)
        log_lms = np.log10(lms)
        lab = np.dot(log_lms, self.LMS_TO_LAB.T)
        return lab

    def _lab_to_rgb(self, lab: np.ndarray, shape: Tuple[int, int, int]) -> np.ndarray:
        log_lms = np.dot(lab, self.LAB_TO_LMS.T)
        lms = np.power(10.0, log_lms)
        rgb = np.dot(lms, self.LMS_TO_RGB.T)
        rgb = np.clip(rgb * 255.0, 0.0, 255.0).astype(np.uint8)
        return rgb.reshape(shape)

    def transform(self, img_rgb: np.ndarray, shift_intensity: float = 1.0) -> np.ndarray:
        """
        Applies color normalization or shift towards target statistics.
        If shift_intensity == 0.0, returns an exact copy of the input.
        """
        if abs(shift_intensity) < 1e-6:
            return img_rgb.copy()

        h, w, c = img_rgb.shape
        lab = self._rgb_to_lab(img_rgb)
        src_means = np.mean(lab, axis=0)
        src_stds = np.std(lab, axis=0) + 1e-6

        norm_lab = (lab - src_means) / src_stds
        eff_stds = (1.0 - shift_intensity) * src_stds + shift_intensity * self.target_stds
        eff_means = (1.0 - shift_intensity) * src_means + shift_intensity * self.target_means

        transformed_lab = (norm_lab * eff_stds) + eff_means
        return self._lab_to_rgb(transformed_lab, (h, w, 3))


# Benchmark Stain Shift Profiles
# Descriptions reflect synthetic manipulation parameters rather than unverified clinical/scanner claims.
STAIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "original": {
        "alpha_h": 1.0,
        "alpha_e": 1.0,
        "stain_rot_deg": 0.0,
        "description": "Baseline unperturbed H&E patch (exact original pixels)"
    },
    "reconstruction_only": {
        "alpha_h": 1.0,
        "alpha_e": 1.0,
        "stain_rot_deg": 0.0,
        "description": "Macenko deconvolution and reconstruction control (reconstruction artifacts only)"
    },
    "heavy_hematoxylin": {
        "alpha_h": 1.65,
        "alpha_e": 0.85,
        "stain_rot_deg": 3.0,
        "description": "Synthetic heavy hematoxylin: dark hyperchromatic nuclei bias"
    },
    "heavy_eosin": {
        "alpha_h": 0.75,
        "alpha_e": 1.65,
        "stain_rot_deg": -3.0,
        "description": "Synthetic heavy eosin: vivid pink cytoplasm and stroma dominance"
    },
    "pale_understained": {
        "alpha_h": 0.60,
        "alpha_e": 0.60,
        "stain_rot_deg": 0.0,
        "description": "Synthetic understained: reduced overall dye concentration and contrast"
    },
    "dark_overstained": {
        "alpha_h": 1.50,
        "alpha_e": 1.50,
        "stain_rot_deg": 0.0,
        "description": "Synthetic overstained: high global dye absorption"
    },
    "synthetic_warm_shift": {
        "alpha_h": 0.90,
        "alpha_e": 1.30,
        "stain_rot_deg": 8.0,
        "description": "Synthetic warm shift: increased eosin and positive stain rotation"
    },
    "synthetic_cool_shift": {
        "alpha_h": 1.35,
        "alpha_e": 0.80,
        "stain_rot_deg": -8.0,
        "description": "Synthetic cool shift: increased hematoxylin and negative stain rotation"
    },
    # Backward compatibility aliases for legacy presets
    "scanner_warm_shift": {
        "alpha_h": 0.90,
        "alpha_e": 1.30,
        "stain_rot_deg": 8.0,
        "description": "Synthetic warm shift (legacy alias)"
    },
    "scanner_cool_shift": {
        "alpha_h": 1.35,
        "alpha_e": 0.80,
        "stain_rot_deg": -8.0,
        "description": "Synthetic cool shift (legacy alias)"
    }
}

LEGACY_PROFILE_ALIASES: Dict[str, str] = {
    "scanner_warm_shift": "synthetic_warm_shift",
    "scanner_cool_shift": "synthetic_cool_shift",
}

DISTINCT_STAIN_PROFILES: List[str] = [p for p in STAIN_PROFILES if p not in LEGACY_PROFILE_ALIASES]



def apply_stain_profile(img_rgb: np.ndarray, profile_name: str) -> np.ndarray:
    """
    Applies one of the benchmark stain profiles to an RGB patch.

    Guarantees:
    - 'original' returns an exact pixel copy without deconvolution loss.
    - 'reconstruction_only' applies deconvolution and reconstruction without perturbation.
    - Perturbation profiles use Macenko deconvolution with numerical safeguards.
    - Unsupported profiles raise ValueError with list of valid options.
    """
    if profile_name not in STAIN_PROFILES:
        raise ValueError(
            f"Unknown stain profile: '{profile_name}'. Supported profiles: {list(STAIN_PROFILES.keys())}"
        )

    if profile_name == "original":
        return img_rgb.copy()

    decomposer = MacenkoStainDecomposer()
    if profile_name == "reconstruction_only":
        return decomposer.reconstruct(img_rgb)

    cfg = STAIN_PROFILES[profile_name]
    return decomposer.perturb(
        img_rgb,
        alpha_h=cfg["alpha_h"],
        alpha_e=cfg["alpha_e"],
        stain_rot_deg=cfg["stain_rot_deg"]
    )
