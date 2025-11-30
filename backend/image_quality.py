from typing import Dict, Any

from PIL import Image, ImageStat, ImageFilter
import numpy as np


def _to_rgb(image: Image.Image) -> Image.Image:
    """Ensure the image is in RGB mode."""
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _compute_lighting_score(image: Image.Image) -> float:
    """
    Estimate lighting based on average brightness.
    Returns a score in [0, 1], where ~0.7–1.0 is nicely lit.
    """
    gray = _to_rgb(image).convert("L")
    stat = ImageStat.Stat(gray)
    mean_brightness = stat.mean[0]  # 0..255

    # Map brightness to [0,1] with a "good" range in the middle
    # Very dark or very bright images get a lower score.
    if mean_brightness < 40 or mean_brightness > 230:
        return 0.1
    if 40 <= mean_brightness <= 80:
        return 0.4
    if 80 < mean_brightness <= 200:
        return 0.8
    if 200 < mean_brightness <= 230:
        return 0.5
    return 0.3


def _compute_framing_score(image: Image.Image) -> float:
    """
    Very simple framing heuristic:
    - Compare edge energy in the center vs. the border.
    - If the center has more edges, we assume the subject is centered.
    """
    rgb = _to_rgb(image)
    w, h = rgb.size

    # Center region (middle 50%) and "border" region (rest)
    cx1, cy1 = int(w * 0.25), int(h * 0.25)
    cx2, cy2 = int(w * 0.75), int(h * 0.75)

    center = rgb.crop((cx1, cy1, cx2, cy2))
    border = rgb.copy()
    border_draw = Image.new("RGB", (w, h), (0, 0, 0))
    border_draw.paste(rgb, mask=None)
    border_draw.paste(Image.new("RGB", (cx2 - cx1, cy2 - cy1), (0, 0, 0)), (cx1, cy1))

    center_edges = center.filter(ImageFilter.FIND_EDGES)
    border_edges = border_draw.filter(ImageFilter.FIND_EDGES)

    center_energy = np.mean(np.array(center_edges))
    border_energy = np.mean(np.array(border_edges))

    ratio = center_energy / (border_energy + 1e-6)
    if ratio > 1.5:
        return 0.9
    if 1.0 < ratio <= 1.5:
        return 0.7
    if 0.7 < ratio <= 1.0:
        return 0.5
    return 0.3


def _compute_background_score(image: Image.Image) -> float:
    """
    Simple background clutter heuristic:
    - Detect edges in the whole image.
    - Many edges -> busy background, fewer -> clean.
    """
    rgb = _to_rgb(image)
    edges = rgb.filter(ImageFilter.FIND_EDGES)
    arr = np.array(edges).astype("float32")

    edge_strength = np.mean(arr)  # 0..255

    if edge_strength < 10:
        return 0.9  # very clean background
    if 10 <= edge_strength <= 30:
        return 0.7
    if 30 < edge_strength <= 60:
        return 0.5
    return 0.3  # very busy background


def _compute_expression_score(image: Image.Image) -> float:
    """
    Placeholder for expression analysis.

    In a full system we would use a face detection + expression classifier.
    For this prototype, we approximate expression / approachability using
    overall contrast (stddev in grayscale).
    """
    rgb = _to_rgb(image)
    gray = rgb.convert("L")
    stat = ImageStat.Stat(gray)
    std_dev = stat.stddev[0]  # contrast proxy

    if std_dev < 20:
        return 0.4  # low contrast -> potentially less expressive
    if 20 <= std_dev <= 50:
        return 0.7
    return 0.85  # strong contrast


def analyze_profile_photo(pil_image: Image.Image) -> Dict[str, Any]:
    """
    Main entry point for analyzing a profile photo.
    Returns a dictionary with individual scores and an overall score.
    """
    # Normalize size for stability
    pil_image = pil_image.copy()
    pil_image.thumbnail((512, 512))

    lighting_score = _compute_lighting_score(pil_image)
    framing_score = _compute_framing_score(pil_image)
    background_score = _compute_background_score(pil_image)
    expression_score = _compute_expression_score(pil_image)

    # Simple weighted average for overall professional score
    professional_score = float(
        0.35 * lighting_score
        + 0.25 * framing_score
        + 0.20 * background_score
        + 0.20 * expression_score
    )

    return {
        "lighting_score": lighting_score,
        "framing_score": framing_score,
        "background_score": background_score,
        "expression_score": expression_score,
        "professional_score": professional_score,
        "notes": [
            "Scores are heuristic and based on simple image statistics.",
            "Higher scores indicate more professional-looking profile photos.",
        ],
    }
