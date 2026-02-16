"""Design phase tools for conducting interviews and generating design artifacts."""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from anthropic import Anthropic

from src.config import (
    PROJECTS_DIR,
    ANTHROPIC_API_KEY,
    SKETCH_PROMPT_CACHE_ENABLED,
    IMAGE_PROMPT_CACHE_ENABLED,
)

logger = logging.getLogger(__name__)

# Initialize Anthropic client for prompt engineering
_anthropic_client = None

def _get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client

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


def _get_sketches_dir(project_name: str) -> Path:
    """Get the path to the sketches directory for a project."""
    sketches_dir = Path(PROJECTS_DIR) / project_name / "design" / "sketches"
    sketches_dir.mkdir(parents=True, exist_ok=True)
    return sketches_dir


def _load_sketches_metadata(project_name: str) -> dict:
    """Load existing sketches metadata or create new."""
    sketches_dir = _get_sketches_dir(project_name)
    metadata_path = sketches_dir / "metadata.json"

    if metadata_path.exists():
        with open(metadata_path) as f:
            return json.load(f)

    return {"sketches": []}


def _save_sketches_metadata(project_name: str, metadata: dict) -> None:
    """Save sketches metadata to disk."""
    sketches_dir = _get_sketches_dir(project_name)
    metadata_path = sketches_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def _engineer_sketch_prompts(design_brief: dict) -> list[str]:
    """Engineer image generation prompts from design brief using Claude.

    Returns list of 3-5 distinct prompt variations for sketch generation.
    """
    client = _get_anthropic_client()

    # Build context from design brief
    brief_context = f"""Design Brief:
- Name: {design_brief.get('name', 'Unnamed')}
- Purpose: {design_brief.get('purpose', 'Not specified')}
- Dimensions: {design_brief.get('dimensions', {})}
- Materials: {', '.join(design_brief.get('materials', ['PLA']))}
- Aesthetics: {design_brief.get('aesthetics', 'Not specified')}
- Constraints: {', '.join(design_brief.get('constraints', []))}
- Special Requirements: {', '.join(design_brief.get('special_requirements', []))}"""

    prompt = f"""{brief_context}

Generate 5 distinct image generation prompts for creating conceptual sketches of this design.
Each prompt should:
1. Emphasize form and proportion over detail
2. Request a specific viewing angle or perspective
3. Include the aesthetic style and material finish
4. Be suitable for image generation AI models (like DALL-E or Midjourney)
5. Be uniquely different from the others

Format your response as a JSON array of exactly 5 strings, each being a complete prompt.
Return ONLY the JSON array, no other text."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    try:
        # Parse the response as JSON
        response_text = message.content[0].text
        prompts = json.loads(response_text)

        # Ensure we have exactly 5 prompts
        if isinstance(prompts, list) and len(prompts) >= 3:
            return prompts[:5]  # Return up to 5
        else:
            logger.warning("Failed to parse prompts from Claude, using fallback")
            return _generate_fallback_prompts(design_brief)
    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        logger.warning(f"Error parsing Claude response: {e}, using fallback prompts")
        return _generate_fallback_prompts(design_brief)


def _generate_fallback_prompts(design_brief: dict) -> list[str]:
    """Generate fallback prompts if Claude prompt engineering fails."""
    name = design_brief.get('name', 'product')
    aesthetics = design_brief.get('aesthetics', 'modern')
    materials_list = design_brief.get('materials', ['PLA'])
    materials = materials_list[0] if materials_list else 'PLA'

    return [
        f"Conceptual sketch of a {name}, {aesthetics} design in {materials}, front view, clean lines, minimalist style",
        f"3D perspective sketch of {name}, {aesthetics} aesthetic, showing depth and proportion, 3/4 view",
        f"Side profile sketch of {name}, functional design, emphasizing form and balance",
        f"Technical conceptual sketch of {name}, {aesthetics} style, top-down view, clear proportions",
        f"Artistic rendering of {name}, {aesthetics} finish, highlighting material texture and surface details",
    ]


def _create_sketch_record(sketch_id: str, variation_num: int, prompt: str) -> dict:
    """Create a sketch metadata record."""
    return {
        "id": sketch_id,
        "variation": variation_num,
        "prompt": prompt,
        "created_at": datetime.now().isoformat(),
        "status": "pending_generation",
        "image_path": None,
        "annotations": []
    }


def _get_images_dir(project_name: str) -> Path:
    """Get the path to the images directory for a project."""
    images_dir = Path(PROJECTS_DIR) / project_name / "design" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def _load_images_metadata(project_name: str) -> dict:
    """Load existing images metadata or create new."""
    images_dir = _get_images_dir(project_name)
    metadata_path = images_dir / "metadata.json"

    if metadata_path.exists():
        with open(metadata_path) as f:
            return json.load(f)

    return {"images": []}


def _save_images_metadata(project_name: str, metadata: dict) -> None:
    """Save images metadata to disk."""
    images_dir = _get_images_dir(project_name)
    metadata_path = images_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def _create_image_record(
    image_id: str,
    sketch_id: str,
    perspective: str,
    prompt: str,
    material_context: str
) -> dict:
    """Create an image metadata record."""
    return {
        "id": image_id,
        "sketch_id": sketch_id,
        "perspective": perspective,
        "prompt": prompt,
        "material_context": material_context,
        "created_at": datetime.now().isoformat(),
        "status": "pending_generation",
        "image_path": None,
    }


def _engineer_image_prompts(
    design_brief: dict,
    sketch_id: str,
    perspective: str,
    feedback: Optional[str] = None
) -> list[str]:
    """Engineer production-quality render prompts from design brief using Claude.

    Returns list of 1 prompt string for the specified perspective.
    """
    client = _get_anthropic_client()

    # Build context from design brief
    brief_context = f"""Design Brief:
- Name: {design_brief.get('name', 'Unnamed')}
- Purpose: {design_brief.get('purpose', 'Not specified')}
- Dimensions: {design_brief.get('dimensions', {})}
- Materials: {', '.join(design_brief.get('materials', ['PLA']))}
- Aesthetics: {design_brief.get('aesthetics', 'Not specified')}
- Constraints: {', '.join(design_brief.get('constraints', []))}
- Special Requirements: {', '.join(design_brief.get('special_requirements', []))}"""

    perspective_context = f"\nDesired Perspective: {perspective.upper()}"
    feedback_context = f"\nUser Feedback for Regeneration: {feedback}" if feedback else ""

    prompt = f"""{brief_context}{perspective_context}{feedback_context}

Generate ONE production-quality render prompt for this design from the specified perspective.
The prompt should:
1. Emphasize realistic materials, lighting, and surface details
2. Include the aesthetic style and material finish
3. Request a specific viewing angle or perspective
4. Be suitable for high-end 3D rendering or image generation (like DALL-E 3 or Midjourney v6)
5. Include lighting and material quality context for photorealistic rendering

Format your response as a JSON array containing exactly 1 string (the prompt).
Return ONLY the JSON array, no other text."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    try:
        # Parse the response as JSON
        response_text = message.content[0].text
        prompts = json.loads(response_text)

        # Ensure we have exactly 1 prompt
        if isinstance(prompts, list) and len(prompts) >= 1:
            return prompts[:1]  # Return exactly 1
        else:
            logger.warning("Failed to parse prompts from Claude, using fallback")
            return _generate_fallback_image_prompts(design_brief, perspective)
    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        logger.warning(f"Error parsing Claude response: {e}, using fallback prompts")
        return _generate_fallback_image_prompts(design_brief, perspective)


def _generate_fallback_image_prompts(design_brief: dict, perspective: str) -> list[str]:
    """Generate fallback production-quality render prompts if Claude fails."""
    name = design_brief.get('name', 'product')
    aesthetics = design_brief.get('aesthetics', 'modern')
    materials_list = design_brief.get('materials', ['PLA'])
    materials = materials_list[0] if materials_list else 'PLA'

    perspective_descriptions = {
        "front": "front-facing view with clear detail and lighting",
        "side": "side profile view showing depth and form",
        "3d": "three-quarter isometric view showing multiple surfaces",
        "top": "top-down overhead view with shadows for depth",
    }

    desc = perspective_descriptions.get(perspective, "detailed view")

    return [
        f"High-quality product render of a {name}, {aesthetics} design in {materials}, {desc}, professional studio lighting, photorealistic materials, fine detail, clean shadows"
    ]


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

    Uses Claude to engineer distinct image generation prompts, then creates
    sketch records with metadata for storing the generated images.

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

    try:
        # Load existing metadata to check cache
        sketches_dir = _get_sketches_dir(project_name)
        metadata = _load_sketches_metadata(project_name)

        # Check if we have cached sketches with the same brief hash
        current_brief_hash = str(hash(json.dumps(design_brief, sort_keys=True)))
        stored_hash = metadata.get("design_brief_hash")

        if (SKETCH_PROMPT_CACHE_ENABLED
                and stored_hash == current_brief_hash
                and len(metadata.get("sketches", [])) > 0):
            # Return cached sketches without calling Claude
            cached_sketches = metadata["sketches"]
            logger.info(
                f"generate_sketches: returning {len(cached_sketches)} cached sketches for {project_name} "
                f"(brief unchanged)"
            )
            prompts = [s.get("prompt", "Cached sketch") for s in cached_sketches]
            return {
                "status": "ok",
                "sketches": cached_sketches,
                "sketch_count": len(cached_sketches),
                "output_dir": str(sketches_dir),
                "prompts": prompts,
                "message": f"Returned {len(cached_sketches)} cached sketch variations (brief unchanged)"
            }

        # Engineer prompts from design brief using Claude
        prompts = _engineer_sketch_prompts(design_brief)
        logger.info(f"generate_sketches: engineered {len(prompts)} prompts for {project_name}")

        # Create sketch records with metadata
        sketches = []

        for variation_num, prompt in enumerate(prompts, 1):
            sketch_id = f"sketch_{uuid.uuid4().hex[:8]}"
            sketch_record = _create_sketch_record(sketch_id, variation_num, prompt)

            # Create a subdirectory for this sketch
            sketch_dir = sketches_dir / sketch_id
            sketch_dir.mkdir(parents=True, exist_ok=True)

            # Save the prompt for reference
            prompt_path = sketch_dir / "prompt.txt"
            with open(prompt_path, "w") as f:
                f.write(prompt)

            sketches.append(sketch_record)

        # Update and save metadata
        metadata["sketches"].extend(sketches)
        metadata["last_updated"] = datetime.now().isoformat()
        metadata["design_brief_hash"] = current_brief_hash
        _save_sketches_metadata(project_name, metadata)

        logger.info(f"generate_sketches: created {len(sketches)} sketch records for {project_name}")

        return {
            "status": "ok",
            "sketches": sketches,
            "sketch_count": len(sketches),
            "output_dir": str(sketches_dir),
            "prompts": prompts,
            "message": f"Generated {len(sketches)} sketch variations with engineered prompts"
        }

    except Exception as e:
        logger.error(f"generate_sketches: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate sketches: {str(e)}"
        }


def _load_design_brief(project_name: str) -> dict:
    """Load design brief from interview.json if it exists."""
    interview_path = Path(PROJECTS_DIR) / project_name / "design" / "interview.json"
    design_brief = {}
    if interview_path.exists():
        with open(interview_path) as f:
            interview_data = json.load(f)
            design_brief = interview_data.get("design_brief", {})
    return design_brief


async def generate_images(
    project_name: str,
    sketch_id: str,
    perspective: str = "front",
    feedback: Optional[str] = None
) -> dict:
    """Generate detailed images from sketch with specified perspective.

    Args:
        project_name: Name of the project (non-empty)
        sketch_id: ID of the sketch to generate images from (non-empty)
        perspective: Viewing perspective ("front", "side", "3d", "top"), defaults to "front"
        feedback: Optional user feedback for image regeneration

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - images: list[dict] with image metadata
        - image_count: int
        - output_dir: str
        - perspective: str (the perspective used)
        - message: str (for ok or error)
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

    # Validate perspective
    valid_perspectives = {"front", "side", "3d", "top"}
    if perspective not in valid_perspectives:
        logger.warning(f"generate_images: invalid perspective '{perspective}'")
        return {
            "status": "error",
            "message": f"perspective must be one of: {', '.join(sorted(valid_perspectives))}"
        }

    try:
        # Get output directory
        images_dir = _get_images_dir(project_name)

        # Load existing metadata
        metadata = _load_images_metadata(project_name)

        # Load design brief
        design_brief = _load_design_brief(project_name)

        # Check for cached prompt file
        prompt_filename = f"{sketch_id}_{perspective}_prompt.txt"
        prompt_filepath = images_dir / prompt_filename

        prompt = None
        if (IMAGE_PROMPT_CACHE_ENABLED
                and prompt_filepath.exists()
                and not feedback):
            # Use cached prompt (bypass Claude if no feedback for refinement)
            with open(prompt_filepath) as f:
                prompt = f.read().strip()
            logger.info(
                f"generate_images: using cached prompt for {sketch_id} perspective {perspective}"
            )
        else:
            # Engineer production-quality render prompt
            prompts = _engineer_image_prompts(design_brief, sketch_id, perspective, feedback)
            prompt = prompts[0] if prompts else "High-quality render of the designed product"

            # Write prompt to cache file for future use
            prompt_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(prompt_filepath, "w") as f:
                f.write(prompt)

        # Build material context for metadata
        materials = design_brief.get("materials", ["PLA"])
        material_context = f"{materials[0]} with professional finish" if materials else "Standard material"

        # Generate image ID and create subdirectory
        image_id = f"image_{uuid.uuid4().hex[:8]}"
        image_dir = images_dir / image_id
        image_dir.mkdir(parents=True, exist_ok=True)

        # Write prompt to file
        prompt_path = image_dir / "prompt.txt"
        with open(prompt_path, "w") as f:
            f.write(prompt)

        # Create image record
        image_record = _create_image_record(
            image_id,
            sketch_id,
            perspective,
            prompt,
            material_context
        )

        # Update metadata
        metadata["images"].append(image_record)
        metadata["last_updated"] = datetime.now().isoformat()
        _save_images_metadata(project_name, metadata)

        logger.info(f"generate_images: created image {image_id} for {project_name} perspective {perspective}")

        return {
            "status": "ok",
            "images": [image_record],
            "image_count": 1,
            "output_dir": str(images_dir),
            "perspective": perspective,
            "message": f"Generated image for {perspective} perspective"
        }

    except Exception as e:
        logger.error(f"generate_images: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate images: {str(e)}"
        }


def _get_blueprint_design_dir(project_name: str) -> Path:
    """Get/create the design directory for blueprint output."""
    design_dir = Path(PROJECTS_DIR) / project_name / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    return design_dir


def _calculate_specifications(design_brief: dict) -> dict:
    """Calculate derived spec values from design brief.

    Args:
        design_brief: Design brief dict with object details

    Returns:
        dict with calculated specifications
    """
    dims = design_brief.get("dimensions", {})
    materials = design_brief.get("materials", ["PLA"])
    constraints = design_brief.get("constraints", [])
    special_reqs = design_brief.get("special_requirements", [])

    # Calculate wall thickness based on material (PLA default 2mm, PETG 2.5mm, Resin 1.5mm)
    material = materials[0] if materials else "PLA"
    wall_thickness = {"PETG": 2.5, "Resin": 1.5}.get(material, 2.0)

    # Calculate infill based on purpose/constraints
    infill = 20  # default
    if any("strong" in c.lower() or "load" in c.lower() for c in constraints + special_reqs):
        infill = 40

    # Estimate weight from volume (rough approximation)
    try:
        width = float(dims.get("width", 100))
        height = float(dims.get("height", 100))
        depth = float(dims.get("depth", 100))
    except (ValueError, TypeError):
        width = height = depth = 100

    volume_cm3 = (width * height * depth / 1000) * (infill / 100)
    density = {"PETG": 1.27, "Resin": 1.2}.get(material, 1.24)  # g/cm³
    weight_g = round(volume_cm3 * density, 1)

    # Estimate print time (very rough: ~10g per hour for average prints)
    print_time = round(weight_g / 10, 1)  # hours

    # Determine support requirement
    needs_supports = False  # default; real detection would need geometry

    # Determine orientation
    orientation = "flat"  # default

    return {
        "overall_dimensions": dims,
        "material": material,
        "wall_thickness_mm": wall_thickness,
        "infill_percentage": infill,
        "print_orientation": orientation,
        "supports_required": needs_supports,
        "support_type": "tree" if needs_supports else "none",
        "estimated_weight_g": weight_g,
        "estimated_print_time_hours": print_time,
    }


def _generate_blueprint_markdown(
    project_name: str,
    design_brief: dict,
    specifications: dict,
    has_assembly: bool = False
) -> str:
    """Generate the blueprint markdown document.

    Args:
        project_name: Name of the project
        design_brief: Design brief dict
        specifications: Calculated specifications dict
        has_assembly: Whether the design has multiple parts

    Returns:
        str with markdown content
    """
    dims = specifications["overall_dimensions"]
    now = datetime.now().strftime("%Y-%m-%d")
    constraints = design_brief.get("constraints", [])
    special_reqs = design_brief.get("special_requirements", [])

    lines = [
        f"# Blueprint: {project_name}",
        f"*Generated: {now}*",
        "",
        "## Design Summary",
        f"- **Purpose:** {design_brief.get('purpose', 'Not specified')}",
        f"- **Aesthetics:** {design_brief.get('aesthetics', 'Not specified')}",
    ]
    if constraints:
        lines.append(f"- **Constraints:** {', '.join(constraints)}")
    if special_reqs:
        lines.append(f"- **Special Requirements:** {', '.join(special_reqs)}")

    lines += [
        "",
        "## Specifications",
        f"- **Overall Dimensions:** {dims.get('width')}mm × {dims.get('height')}mm × {dims.get('depth')}mm",
        f"- **Material:** {specifications['material']}",
        f"- **Wall Thickness:** {specifications['wall_thickness_mm']}mm",
        f"- **Infill:** {specifications['infill_percentage']}%",
        "",
        "## Print Parameters",
        f"- **Orientation:** {specifications['print_orientation']}",
        f"- **Supports:** {'Yes (' + specifications['support_type'] + ')' if specifications['supports_required'] else 'No'}",
        f"- **Estimated Print Time:** {specifications['estimated_print_time_hours']} hours",
        f"- **Estimated Weight:** {specifications['estimated_weight_g']}g",
    ]

    if has_assembly:
        lines += [
            "",
            "## Assembly",
            "See assembly instructions in the parts list below.",
        ]

    lines += [
        "",
        "## Notes",
        "- Verify dimensions match real-world fit requirements before printing.",
        "- Adjust infill and wall thickness based on functional requirements.",
    ]

    return "\n".join(lines)


def _generate_specs_json(
    project_name: str,
    design_brief: dict,
    specifications: dict,
    approved_images: list
) -> dict:
    """Generate the specs.json structure for the modeling agent.

    Args:
        project_name: Name of the project
        design_brief: Design brief dict
        specifications: Calculated specifications dict
        approved_images: List of approved image IDs

    Returns:
        dict with JSON-serializable specification structure
    """
    return {
        "project_id": str(uuid.uuid4()),
        "project_name": project_name,
        "created_at": datetime.now().isoformat(),
        "design_brief": design_brief,
        "specifications": specifications,
        "approved_images": approved_images,
        "parts": [
            {
                "name": "main_body",
                "quantity": 1,
                "dimensions": specifications.get("overall_dimensions", {}),
                "tolerance_mm": 0.2,
            }
        ],
        "assembly_instructions": [],
    }


async def generate_blueprint(
    project_name: str,
    design_brief: dict,
    approved_images: list = None
) -> dict:
    """Generate formal technical blueprint and specifications.

    Args:
        project_name: Name of the project
        design_brief: Design brief dict with object details
        approved_images: List of approved image IDs (optional)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - blueprint_path: str path to blueprint markdown
        - specs_path: str path to specs JSON
        - message: str (if status is "error")
    """
    logger.info(
        f"generate_blueprint called: project={project_name}, brief_keys={list(design_brief.keys())}, images={len(approved_images or [])}"
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

    try:
        # Get/create design directory
        design_dir = _get_blueprint_design_dir(project_name)

        # Calculate specifications
        specifications = _calculate_specifications(design_brief)

        # Check if multi-part (for future enhancement)
        has_assembly = len(design_brief.get("special_requirements", [])) > 0

        # Generate markdown blueprint
        blueprint_md = _generate_blueprint_markdown(
            project_name,
            design_brief,
            specifications,
            has_assembly
        )

        # Write blueprint.md
        blueprint_path = design_dir / "blueprint.md"
        with open(blueprint_path, "w") as f:
            f.write(blueprint_md)

        # Generate specs.json
        specs_data = _generate_specs_json(
            project_name,
            design_brief,
            specifications,
            approved_images or []
        )

        # Write design_specs.json
        specs_path = design_dir / "design_specs.json"
        with open(specs_path, "w") as f:
            json.dump(specs_data, f, indent=2)

        logger.info(f"generate_blueprint: created blueprint and specs for {project_name}")

        return {
            "status": "ok",
            "blueprint_path": str(blueprint_path),
            "specs_path": str(specs_path),
            "message": f"Generated blueprint and specifications for {project_name}"
        }

    except Exception as e:
        logger.error(f"generate_blueprint: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate blueprint: {str(e)}"
        }
