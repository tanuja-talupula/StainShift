"""
StainShift: Physics-based Stain Deconvolution, Perturbation, and Normalization
Implements Beer-Lambert optical density deconvolution (Macenko et al.) and
Reinhard Ruderman l-alpha-beta color transfer for digital histopathology.
100% pure NumPy / PIL - no OpenCV dependency required.
"""

import numpy as np
from PIL import Image
import torch


class MacenkoStainDecomposer:
    """
    Decomposes an H&E RGB image into Hematoxylin and Eosin stain vectors and concentrations
    using the Macenko method (optical density PCA).
    """

    def __init__(self, alpha=1.0, beta=0.15):
        self.alpha = alpha  # percentile for robust angle estimation (e.g., 1st and 99th)
        self.beta = beta    # optical density threshold to discard background

    def rgb_to_od(self, img_rgb: np.ndarray) -> np.ndarray:
        """Converts RGB image [0, 255] to Optical Density (OD) space via Beer-Lambert."""
        img = img_rgb.astype(np.float64)
        img = np.clip(img, 1.0, 255.0)
        od = -np.log10(img / 255.0)
        return od

    def od_to_rgb(self, od: np.ndarray) -> np.ndarray:
        """Converts Optical Density back to RGB image [0, 255]."""
        img = 255.0 * np.power(10.0, -od)
        img = np.clip(img, 0.0, 255.0).astype(np.uint8)
        return img

    def extract_stain_vectors_and_concentrations(self, img_rgb: np.ndarray):
        """
        Calculates the 2x3 stain matrix (Hematoxylin and Eosin vectors)
        and the (H*W, 2) concentration map for the image.
        """
        od = self.rgb_to_od(img_rgb)
        h, w, c = od.shape
        od_flat = od.reshape((-1, 3))

        # Filter out optical density below beta (transparent glass/background)
        mask = np.all(od_flat > self.beta, axis=1)
        od_filtered = od_flat[mask]

        if len(od_filtered) < 100:
            # Fallback to standard canonical H&E vectors if patch is mostly blank/background
            he_matrix = np.array([
                [0.644211, 0.716556, 0.266844],  # Hematoxylin canonical OD
                [0.092783, 0.954111, 0.283111]   # Eosin canonical OD
            ])
            he_matrix = he_matrix / np.linalg.norm(he_matrix, axis=1, keepdims=True)
            concentrations = np.linalg.lstsq(he_matrix.T, od_flat.T, rcond=None)[0].T
            return he_matrix, np.maximum(concentrations, 0.0), (h, w)

        # 1. Covariance matrix of filtered OD values
        cov = np.cov(od_filtered, rowvar=False)

        # 2. Eigenvectors of covariance matrix
        eigvals, eigvecs = np.linalg.eigh(cov)
        top_eigvecs = eigvecs[:, [2, 1]]

        # 3. Project filtered OD values onto the 2D plane
        projected = np.dot(od_filtered, top_eigvecs)

        # 4. Compute angles on the 2D projection
        angles = np.arctan2(projected[:, 1], projected[:, 0])

        # 5. Find robust extreme angles (alpha and 100-alpha percentiles)
        min_angle = np.percentile(angles, self.alpha)
        max_angle = np.percentile(angles, 100.0 - self.alpha)

        v_min = np.dot(top_eigvecs, np.array([np.cos(min_angle), np.sin(min_angle)]))
        v_max = np.dot(top_eigvecs, np.array([np.cos(max_angle), np.sin(max_angle)]))

        # Order: [Hematoxylin, Eosin]
        if v_min[0] > v_max[0]:
            stain_matrix = np.vstack([v_min, v_max])
        else:
            stain_matrix = np.vstack([v_max, v_min])

        stain_matrix = stain_matrix / np.linalg.norm(stain_matrix, axis=1, keepdims=True)

        # 6. Solve for concentrations: OD = C * S  => C = OD * S^+
        concentrations = np.linalg.lstsq(stain_matrix.T, od_flat.T, rcond=None)[0].T
        concentrations = np.maximum(concentrations, 0.0)

        return stain_matrix, concentrations, (h, w)

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
        """
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
            s_perturbed /= np.linalg.norm(s_perturbed, axis=1, keepdims=True)

        if add_noise > 0.0:
            noise = np.random.normal(0, add_noise, s_perturbed.shape)
            s_perturbed = np.maximum(s_perturbed + noise, 0.0)
            s_perturbed /= np.linalg.norm(s_perturbed, axis=1, keepdims=True)

        od_perturbed = np.dot(c_perturbed, s_perturbed)
        od_perturbed = od_perturbed.reshape((h, w, 3))

        return self.od_to_rgb(od_perturbed)


class ReinhardNormalizer:
    """
    Reinhard color transfer algorithm in Ruderman l-alpha-beta color space.
    Fully pure-numpy implementation (Reinhard et al. 2001).
    """

    RGB_TO_LMS = np.array([
        [0.3811, 0.5783, 0.0402],
        [0.1967, 0.7244, 0.0782],
        [0.0241, 0.1288, 0.8444]
    ])

    LMS_TO_LAB = np.array([
        [1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)],
        [1.0 / np.sqrt(6.0), 1.0 / np.sqrt(6.0), -2.0 / np.sqrt(6.0)],
        [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0), 0.0]
    ])

    LAB_TO_LMS = np.linalg.inv(LMS_TO_LAB)
    LMS_TO_RGB = np.linalg.inv(RGB_TO_LMS)

    def __init__(self, target_means=None, target_stds=None):
        if target_means is None:
            self.target_means = np.array([2.95, 0.12, -0.05])
        else:
            self.target_means = np.array(target_means)

        if target_stds is None:
            self.target_stds = np.array([0.45, 0.10, 0.08])
        else:
            self.target_stds = np.array(target_stds)

    def _rgb_to_lab(self, img_rgb: np.ndarray) -> np.ndarray:
        flat = img_rgb.reshape((-1, 3)).astype(np.float64) / 255.0
        flat = np.clip(flat, 1e-6, 1.0)
        lms = np.dot(flat, self.RGB_TO_LMS.T)
        lms = np.maximum(lms, 1e-6)
        log_lms = np.log10(lms)
        lab = np.dot(log_lms, self.LMS_TO_LAB.T)
        return lab

    def _lab_to_rgb(self, lab: np.ndarray, shape) -> np.ndarray:
        log_lms = np.dot(lab, self.LAB_TO_LMS.T)
        lms = np.power(10.0, log_lms)
        rgb = np.dot(lms, self.LMS_TO_RGB.T)
        rgb = np.clip(rgb * 255.0, 0.0, 255.0).astype(np.uint8)
        return rgb.reshape(shape)

    def transform(self, img_rgb: np.ndarray, shift_intensity: float = 1.0) -> np.ndarray:
        h, w, c = img_rgb.shape
        lab = self._rgb_to_lab(img_rgb)
        src_means = np.mean(lab, axis=0)
        src_stds = np.std(lab, axis=0) + 1e-6

        norm_lab = (lab - src_means) / src_stds
        eff_stds = (1.0 - shift_intensity) * src_stds + shift_intensity * self.target_stds
        eff_means = (1.0 - shift_intensity) * src_means + shift_intensity * self.target_means

        transformed_lab = (norm_lab * eff_stds) + eff_means
        return self._lab_to_rgb(transformed_lab, (h, w, 3))


# Standard Benchmark Stain Shift Profiles (Simulating real multi-hospital & scanner variations)
STAIN_PROFILES = {
    "original": {
        "alpha_h": 1.0,
        "alpha_e": 1.0,
        "stain_rot_deg": 0.0,
        "description": "Baseline unperturbed H&E stain (in-domain)"
    },
    "heavy_hematoxylin": {
        "alpha_h": 1.65,
        "alpha_e": 0.85,
        "stain_rot_deg": 3.0,
        "description": "Lab A: Dark hyperchromatic nuclei, thick tissue slice"
    },
    "heavy_eosin": {
        "alpha_h": 0.75,
        "alpha_e": 1.65,
        "stain_rot_deg": -3.0,
        "description": "Lab B: Vivid pink/red cytoplasm & stroma dominance"
    },
    "pale_understained": {
        "alpha_h": 0.60,
        "alpha_e": 0.60,
        "stain_rot_deg": 0.0,
        "description": "Lab C: Rapid destaining, washed out weak contrast"
    },
    "dark_overstained": {
        "alpha_h": 1.50,
        "alpha_e": 1.50,
        "stain_rot_deg": 0.0,
        "description": "Lab D: High reagent exposure, heavy global absorption"
    },
    "scanner_warm_shift": {
        "alpha_h": 0.90,
        "alpha_e": 1.30,
        "stain_rot_deg": 8.0,
        "description": "Scanner X (Aperio-like): Warm yellowish-red calibration"
    },
    "scanner_cool_shift": {
        "alpha_h": 1.35,
        "alpha_e": 0.80,
        "stain_rot_deg": -8.0,
        "description": "Scanner Y (Hamamatsu-like): Cool bluish-magenta bias"
    }
}


def apply_stain_profile(img_rgb: np.ndarray, profile_name: str) -> np.ndarray:
    """Applies one of the benchmark stain profiles to an RGB patch."""
    if profile_name not in STAIN_PROFILES:
        raise ValueError(f"Unknown stain profile: {profile_name}. Available: {list(STAIN_PROFILES.keys())}")
    cfg = STAIN_PROFILES[profile_name]
    if profile_name == "original":
        return img_rgb.copy()

    decomposer = MacenkoStainDecomposer()
    return decomposer.perturb(
        img_rgb,
        alpha_h=cfg["alpha_h"],
        alpha_e=cfg["alpha_e"],
        stain_rot_deg=cfg["stain_rot_deg"]
    )
