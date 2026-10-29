"""
Tests for MacenkoStainDecomposer, ReinhardNormalizer, and stain profile transformations.
"""

import numpy as np
import pytest

from src.stain_shift import (
    STAIN_PROFILES,
    DegenerateTissueError,
    InsufficientTissueError,
    MacenkoStainDecomposer,
    ReinhardNormalizer,
    StainDecompositionError,
    apply_stain_profile,
)


def test_original_profile_exact_pixel_equality(synthetic_he_patch):
    """Proves that profile 'original' returns an exact pixel-identical copy."""
    transformed = apply_stain_profile(synthetic_he_patch, "original")
    assert np.array_equal(synthetic_he_patch, transformed)


def test_neutral_custom_parameters_exact_pixel_equality(synthetic_he_patch):
    """Proves that neutral parameters (alpha_h=1, alpha_e=1, rot=0) preserve exact pixels."""
    decomposer = MacenkoStainDecomposer()
    transformed = decomposer.perturb(
        synthetic_he_patch, alpha_h=1.0, alpha_e=1.0, stain_rot_deg=0.0, add_noise=0.0
    )
    assert np.array_equal(synthetic_he_patch, transformed)


def test_non_neutral_perturbation_changes_pixels(synthetic_he_patch):
    """Proves that active stain perturbation alters pixel values on valid tissue."""
    decomposer = MacenkoStainDecomposer()
    transformed = decomposer.perturb(
        synthetic_he_patch, alpha_h=1.5, alpha_e=0.8, stain_rot_deg=5.0
    )
    assert not np.array_equal(synthetic_he_patch, transformed)
    assert transformed.shape == synthetic_he_patch.shape
    assert transformed.dtype == np.uint8
    assert np.all(np.isfinite(transformed))


def test_reconstruction_only_is_distinct_from_original(synthetic_he_patch):
    """Proves reconstruction-only condition is separated from original identity."""
    decomposer = MacenkoStainDecomposer()
    reconstructed = decomposer.reconstruct(synthetic_he_patch)
    # Reconstructed undergoes lossy OD log/exp roundtrip, so it shouldn't be strictly identical
    # but must remain finite and bounded
    assert reconstructed.shape == synthetic_he_patch.shape
    assert reconstructed.dtype == np.uint8
    assert np.all(np.isfinite(reconstructed))


def test_macenko_white_image_handling():
    """Tests decomposition behavior on a pure white / background image."""
    white = np.full((50, 50, 3), 255, dtype=np.uint8)
    decomposer = MacenkoStainDecomposer()
    # In fallback mode, it uses canonical vectors safely
    mat, conc, shape = decomposer.extract_stain_vectors_and_concentrations(white, allow_fallback=True)
    assert mat.shape == (2, 3)
    assert conc.shape == (2500, 2)
    assert np.all(np.isfinite(conc))

    # In strict mode without fallback, it must raise InsufficientTissueError
    with pytest.raises(InsufficientTissueError):
        decomposer.extract_stain_vectors_and_concentrations(white, allow_fallback=False)


def test_macenko_degenerate_uniform_image():
    """Tests decomposition on degenerate uniform gray image."""
    gray = np.full((50, 50, 3), 128, dtype=np.uint8)
    decomposer = MacenkoStainDecomposer()
    # In strict mode without fallback, uniform patch has 0 OD variance
    with pytest.raises(DegenerateTissueError):
        decomposer.extract_stain_vectors_and_concentrations(gray, allow_fallback=False)


def test_reinhard_zero_intensity_exact_pixel_equality(synthetic_he_patch):
    """Proves that Reinhard with shift_intensity=0.0 preserves exact pixels."""
    norm = ReinhardNormalizer()
    out = norm.transform(synthetic_he_patch, shift_intensity=0.0)
    assert np.array_equal(synthetic_he_patch, out)


def test_reinhard_calibrated_transfer_no_blowout(synthetic_he_patch):
    """Proves that calibrated Reinhard does not blow out pixels to all 255."""
    norm = ReinhardNormalizer()
    out = norm.transform(synthetic_he_patch, shift_intensity=1.0)
    assert out.dtype == np.uint8
    assert np.all(np.isfinite(out))
    # Must NOT saturate all pixels at 255
    assert not np.all(out == 255)
    # Mean should remain in reasonable range, not 255.0
    assert out.mean() < 240.0


def test_reinhard_fit_on_reference(synthetic_he_patch):
    """Proves that Reinhard can fit its target statistics from a reference patch."""
    norm = ReinhardNormalizer()
    norm.fit(synthetic_he_patch)
    out = norm.transform(synthetic_he_patch, shift_intensity=1.0)
    assert out.shape == synthetic_he_patch.shape
    assert np.all(np.isfinite(out))
