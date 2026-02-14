"""Design phase tools for conducting interviews and generating design artifacts."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from src.config import PROJECTS_DIR

logger = logging.getLogger(__name__)

# Interview questions sequence
INTERVIEW_QUESTIONS = [
    ("object_name", "What would you like to name this project, and what is its primary purpose?"),
    ("dimensions", "What are the approximate dimensions? (e.g. 100mm wide, 80mm deep, 60mm tall)"),
    ("materials", "What material(s) should it be printed in? (e.g. PLA, PETG, Resin)"),
    ("aesthetics", "How would you describe the aesthetic style? (e.g. minimalist, ornate, functional)"),
    ("constraints", "Are there any specific constraints? (e.g. must fit iPhone 14, non-slip base, weight limit)"),
    ("moving_parts", "Does this design have moving parts or multiple pieces that assemble together?"),
    ("special_requirements", "Any other special requirements or existing designs you'd like to reference?"),
]


def _get_interview_path(project_name: str) -> Path:
    """Get the path to the interview.json file for a project."""
    project_dir = Path(PROJECTS_DIR) / project_name / "design"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir / "interview.json"


def _load_interview_state(project_name: str) -> dict:
    """Load existing interview state or create new."""
    interview_path = _get_interview_path(project_name)

    if interview_path.exists():
        with open(interview_path) as f:
            return json.load(f)

    # Create fresh state
    return {
        "project_name": project_name,
        "current_question_index": 0,
        "questions": [q[0] for q in INTERVIEW_QUESTIONS],
        "answers": {},
        "complete": False,
        "design_brief": None,
    }


def _save_interview_state(project_name: str, state: dict) -> None:
    """Save interview state to disk."""
    interview_path = _get_interview_path(project_name)
    with open(interview_path, "w") as f:
        json.dump(state, f, indent=2)


def _parse_dimensions(dims_str: str) -> dict:
    """Parse dimension string into dict with width, height, depth."""
    # Simple parser: handles formats like "100mm x 80mm x 60mm" or "100 80 60"
    import re

    numbers = re.findall(r"(\d+(?:\.\d+)?)", dims_str)

    if len(numbers) >= 3:
        return {
            "width": numbers[0],
            "height": numbers[1],
            "depth": numbers[2],
        }
    elif len(numbers) == 2:
        return {
            "width": numbers[0],
            "height": numbers[1],
            "depth": numbers[0],
        }
    elif len(numbers) == 1:
        return {
            "width": numbers[0],
            "height": numbers[0],
            "depth": numbers[0],
        }
    else:
        # Fallback for unparseable input
        return {
            "width": dims_str,
            "height": dims_str,
            "depth": dims_str,
        }


def _build_design_brief(answers: dict) -> dict:
    """Build design brief from collected answers."""
    # Parse constraints and materials as lists
    constraints_str = answers.get("constraints", "")
    constraints = [c.strip() for c in constraints_str.split(",") if c.strip()]

    materials_str = answers.get("materials", "")
    materials = [m.strip() for m in materials_str.split(",") if m.strip()]

    special_str = answers.get("special_requirements", "")
    special_reqs = [s.strip() for s in special_str.split(",") if s.strip()]

    return {
        "name": answers.get("object_name", ""),
        "purpose": answers.get("object_name", ""),
        "dimensions": _parse_dimensions(answers.get("dimensions", "")),
        "materials": materials or ["PLA"],
        "aesthetics": answers.get("aesthetics", ""),
        "constraints": constraints or [],
        "special_requirements": special_reqs or [],
    }


def _generate_summary(project_name: str, design_brief: dict) -> str:
    """Generate human-readable summary of the design brief."""
    lines = [f"Design Brief Summary for '{project_name}':"]

    if design_brief.get("purpose"):
        lines.append(f"- Purpose: {design_brief['purpose']}")

    dims = design_brief.get("dimensions", {})
    if dims:
        lines.append(f"- Dimensions: {dims.get('width')} x {dims.get('height')} x {dims.get('depth')}mm")

    materials = design_brief.get("materials", [])
    if materials:
        lines.append(f"- Materials: {', '.join(materials)}")

    if design_brief.get("aesthetics"):
        lines.append(f"- Aesthetics: {design_brief['aesthetics']}")

    constraints = design_brief.get("constraints", [])
    if constraints:
        lines.append(f"- Constraints: {', '.join(constraints)}")

    return "\n".join(lines)


async def conduct_interview(user_input: str, project_name: str) -> dict:
    """Conduct structured interview to gather design requirements.

    Args:
        user_input: User's response to the current interview question
        project_name: Name of the project

    Returns:
        dict with keys:
        - status: "in_progress" or "complete" or "error"
        - next_question: str (if status is "in_progress")
        - interview_complete: bool
        - design_brief: dict or None (populated when complete)
        - question_number: int (current question number, 1-indexed)
        - total_questions: int (total number of questions)
        - message: str (if status is "error")
    """
    logger.info(
        f"conduct_interview called: project={project_name}, input_len={len(user_input)}"
    )

    # Validate inputs
    if not isinstance(user_input, str) or not user_input.strip():
        logger.warning("conduct_interview: empty user_input")
        return {
            "status": "error",
            "message": "user_input must be a non-empty string"
        }

    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("conduct_interview: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    # Load existing state
    state = _load_interview_state(project_name)
    current_question_idx = state["current_question_index"]

    # Store the answer to the current question
    # current_question_idx tells us which question we're answering (0-indexed into INTERVIEW_QUESTIONS)
    # This user_input is their response to INTERVIEW_QUESTIONS[current_question_idx]
    if current_question_idx < len(INTERVIEW_QUESTIONS):
        question_key = INTERVIEW_QUESTIONS[current_question_idx][0]
        state["answers"][question_key] = user_input.strip()
        # Question number is 1-indexed for the user
        answered_question_number = current_question_idx + 1
        state["current_question_index"] += 1
    else:
        answered_question_number = len(INTERVIEW_QUESTIONS)

    # Save updated state
    _save_interview_state(project_name, state)

    # Check if interview is now complete (all questions answered)
    if state["current_question_index"] >= len(INTERVIEW_QUESTIONS):
        # Build design brief
        design_brief = _build_design_brief(state["answers"])
        state["complete"] = True
        state["design_brief"] = design_brief
        _save_interview_state(project_name, state)

        summary = _generate_summary(project_name, design_brief)

        logger.info(f"conduct_interview: interview complete for {project_name}")
        return {
            "status": "complete",
            "interview_complete": True,
            "design_brief": design_brief,
            "summary": summary,
            "question_number": answered_question_number,
            "total_questions": len(INTERVIEW_QUESTIONS),
        }

    # Return the next question
    next_question_idx = state["current_question_index"]
    question_key, question_text = INTERVIEW_QUESTIONS[next_question_idx]

    logger.info(
        f"conduct_interview: returning question {next_question_idx + 1}/{len(INTERVIEW_QUESTIONS)} for {project_name}"
    )

    return {
        "status": "in_progress",
        "next_question": question_text,
        "interview_complete": False,
        "design_brief": None,
        "question_number": answered_question_number,
        "total_questions": len(INTERVIEW_QUESTIONS),
    }


async def generate_sketches(project_name: str, design_brief: dict) -> dict:
    """Generate conceptual sketches from design brief.

    Args:
        project_name: Name of the project
        design_brief: Design brief dict with object details

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - sketches: list[dict] with sketch metadata
        - sketch_count: int
        - output_dir: str
        - message: str (if status is "error")
    """
    logger.info(
        f"generate_sketches called: project={project_name}, brief_keys={list(design_brief.keys())}"
    )

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("generate_sketches: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    if not isinstance(design_brief, dict) or len(design_brief) == 0:
        logger.warning("generate_sketches: empty or invalid design_brief")
        return {
            "status": "error",
            "message": "design_brief must be a non-empty dict"
        }

    # Stub implementation: return empty sketch list
    logger.info(f"generate_sketches: returning ok for {project_name}")
    return {
        "status": "ok",
        "sketches": [],
        "sketch_count": 0,
        "output_dir": f"./projects/{project_name}/design/sketches"
    }


async def generate_images(
    project_name: str,
    sketch_id: str,
    perspective: str = "front"
) -> dict:
    """Generate detailed images from sketch with specified perspective.

    Args:
        project_name: Name of the project
        sketch_id: ID of the sketch to generate images from
        perspective: Viewing perspective ("front", "side", "3d", "top")

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - images: list[dict] with image metadata
        - image_count: int
        - output_dir: str
        - message: str (if status is "error")
    """
    logger.info(
        f"generate_images called: project={project_name}, sketch={sketch_id}, perspective={perspective}"
    )

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("generate_images: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    if not isinstance(sketch_id, str) or not sketch_id.strip():
        logger.warning("generate_images: empty sketch_id")
        return {
            "status": "error",
            "message": "sketch_id must be a non-empty string"
        }

    # Stub implementation: return empty image list
    logger.info(f"generate_images: returning ok for {project_name}")
    return {
        "status": "ok",
        "images": [],
        "image_count": 0,
        "output_dir": f"./projects/{project_name}/design/images"
    }


async def generate_blueprint(
    project_name: str,
    design_brief: dict,
    approved_images: list
) -> dict:
    """Generate formal technical blueprint and specifications.

    Args:
        project_name: Name of the project
        design_brief: Design brief dict with object details
        approved_images: List of approved image IDs

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - blueprint_path: str path to blueprint markdown
        - specs_path: str path to specs JSON
        - message: str (if status is "error")
    """
    logger.info(
        f"generate_blueprint called: project={project_name}, brief_keys={list(design_brief.keys())}, images={len(approved_images)}"
    )

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("generate_blueprint: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    if not isinstance(design_brief, dict) or len(design_brief) == 0:
        logger.warning("generate_blueprint: empty or invalid design_brief")
        return {
            "status": "error",
            "message": "design_brief must be a non-empty dict"
        }

    # Stub implementation: return placeholder paths
    logger.info(f"generate_blueprint: returning ok for {project_name}")
    return {
        "status": "ok",
        "blueprint_path": f"./projects/{project_name}/design/blueprint.md",
        "specs_path": f"./projects/{project_name}/design/specs.json"
    }
