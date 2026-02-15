"""Modeling phase tools for generating OpenSCAD models and exporting for printing."""

import json
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.config import PROJECTS_DIR, OPENSCAD_PATH

logger = logging.getLogger(__name__)


def _get_modeling_dir(project_name: str) -> Path:
    """Get the path to the modeling directory for a project."""
    modeling_dir = Path(PROJECTS_DIR) / project_name / "modeling"
    modeling_dir.mkdir(parents=True, exist_ok=True)
    return modeling_dir


def _get_scad_dir(project_name: str) -> Path:
    """Get the path to the scad subdirectory for a project."""
    scad_dir = _get_modeling_dir(project_name) / "scad"
    scad_dir.mkdir(parents=True, exist_ok=True)
    return scad_dir


def _get_exports_dir(project_name: str) -> Path:
    """Get the path to the exports subdirectory for a project."""
    exports_dir = _get_modeling_dir(project_name) / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def _load_modeling_metadata(project_name: str) -> dict:
    """Load existing modeling metadata or create new."""
    modeling_dir = _get_modeling_dir(project_name)
    metadata_path = modeling_dir / "metadata.json"

    if metadata_path.exists():
        with open(metadata_path) as f:
            return json.load(f)

    return {
        "project_name": project_name,
        "created_at": datetime.now().isoformat(),
        "scad_models": [],
        "exports": []
    }


def _save_modeling_metadata(project_name: str, metadata: dict) -> None:
    """Save modeling metadata to disk."""
    modeling_dir = _get_modeling_dir(project_name)
    metadata_path = modeling_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def _validate_export_file(output_file: Path) -> bool:
    """Validate that an exported file exists and has non-zero size.

    Args:
        output_file: Path to the exported file

    Returns:
        True if file exists and has size > 0, False otherwise
    """
    return output_file.exists() and output_file.stat().st_size > 0


def _load_design_specs(project_name: str, specs_path: Optional[str] = None) -> dict:
    """Load design specifications from JSON file."""
    if specs_path:
        # Use explicit path if provided
        target_path = Path(specs_path)
    else:
        # Default to design/design_specs.json
        target_path = Path(PROJECTS_DIR) / project_name / "design" / "design_specs.json"

    if not target_path.exists():
        raise FileNotFoundError(f"Design specs not found at {target_path}")

    with open(target_path) as f:
        return json.load(f)


def _generate_basic_scad(project_name: str, design_specs: dict) -> str:
    """Generate basic OpenSCAD code from design specifications.

    Uses solidpython2 library to generate parametric OpenSCAD models.
    Returns the OpenSCAD code as a string.
    """
    try:
        from solid2 import cube, translate, difference, scad_render
    except ImportError:
        logger.warning("solidpython2 not available, using fallback SCAD generation")
        return _generate_fallback_scad(project_name, design_specs)

    try:
        specs = design_specs.get("specifications", {})
        dims = specs.get("overall_dimensions", {})
        width = float(dims.get("width", 100))
        height = float(dims.get("height", 80))
        depth = float(dims.get("depth", 60))
        wall_thickness = float(specs.get("wall_thickness_mm", 2))
        material = specs.get("material", "PLA")

        # Generate parametric box with walls
        outer = cube([width, height, depth])
        inner = translate([wall_thickness, wall_thickness, wall_thickness])(
            cube([width - 2*wall_thickness, height - 2*wall_thickness, depth - wall_thickness])
        )
        box = difference()(outer, inner)

        # Render to OpenSCAD code
        scad_code = scad_render(box)

        # Add header comments
        header = f"""// Generated OpenSCAD model for {project_name}
// Material: {material}
// Overall dimensions: {width}mm x {height}mm x {depth}mm
// Wall thickness: {wall_thickness}mm

"""
        return header + scad_code

    except Exception as e:
        logger.error(f"Error generating SCAD with solidpython2: {str(e)}", exc_info=True)
        return _generate_fallback_scad(project_name, design_specs)


def _generate_fallback_scad(project_name: str, design_specs: dict) -> str:
    """Generate basic OpenSCAD code as fallback if solidpython2 is unavailable."""
    specs = design_specs.get("specifications", {})
    dims = specs.get("overall_dimensions", {})
    width = dims.get("width", 100)
    height = dims.get("height", 80)
    depth = dims.get("depth", 60)
    wall_thickness = specs.get("wall_thickness_mm", 2)
    material = specs.get("material", "PLA")

    return f"""// Generated OpenSCAD model for {project_name}
// Material: {material}
// Overall dimensions: {width}mm x {height}mm x {depth}mm
// Wall thickness: {wall_thickness}mm

module box(width={width}, height={height}, depth={depth}, wall={wall_thickness}) {{
  difference() {{
    cube([width, height, depth]);
    translate([wall, wall, wall])
      cube([width-2*wall, height-2*wall, depth-wall]);
  }}
}}

box();
"""


async def validate_design_specs(project_name: str, specs_path: Optional[str] = None) -> dict:
    """Validate design specifications from a design phase output.

    Args:
        project_name: Name of the project (non-empty string)
        specs_path: Optional path to design_specs.json (defaults to design/design_specs.json)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - specs: dict (if status is "ok")
        - message: str
    """
    logger.info(f"validate_design_specs called: project={project_name}")

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("validate_design_specs: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    try:
        # Load design specs
        design_specs = _load_design_specs(project_name, specs_path)

        # Validate required keys
        required_keys = ["project_name", "specifications", "design_brief"]
        missing_keys = [k for k in required_keys if k not in design_specs]
        if missing_keys:
            logger.warning(f"validate_design_specs: missing required keys: {missing_keys}")
            return {
                "status": "error",
                "message": f"Design specs missing required keys: {', '.join(missing_keys)}"
            }

        # Validate specifications structure
        specs = design_specs.get("specifications", {})
        spec_required = ["overall_dimensions", "material"]
        spec_missing = [k for k in spec_required if k not in specs]
        if spec_missing:
            logger.warning(f"validate_design_specs: missing specification keys: {spec_missing}")
            return {
                "status": "error",
                "message": f"Specifications missing required keys: {', '.join(spec_missing)}"
            }

        logger.info(f"validate_design_specs: validation successful for {project_name}")
        return {
            "status": "ok",
            "specs": design_specs,
            "message": f"Design specs validated successfully for {project_name}"
        }

    except FileNotFoundError as e:
        logger.error(f"validate_design_specs: file not found: {str(e)}")
        return {
            "status": "error",
            "message": f"Design specs file not found: {str(e)}"
        }
    except json.JSONDecodeError as e:
        logger.error(f"validate_design_specs: invalid JSON: {str(e)}")
        return {
            "status": "error",
            "message": f"Design specs file contains invalid JSON: {str(e)}"
        }
    except Exception as e:
        logger.error(f"validate_design_specs: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to validate design specs: {str(e)}"
        }


async def setup_openscad_workspace(project_name: str) -> dict:
    """Set up OpenSCAD workspace directory structure.

    Args:
        project_name: Name of the project (non-empty string)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - workspace_dir: str (path to modeling directory)
        - message: str
    """
    logger.info(f"setup_openscad_workspace called: project={project_name}")

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("setup_openscad_workspace: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    try:
        # Create directory structure
        modeling_dir = _get_modeling_dir(project_name)
        _get_scad_dir(project_name)
        _get_exports_dir(project_name)

        # Create preview directory
        preview_dir = modeling_dir / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metadata
        metadata = {
            "project_name": project_name,
            "created_at": datetime.now().isoformat(),
            "scad_models": [],
            "exports": []
        }
        _save_modeling_metadata(project_name, metadata)

        logger.info(f"setup_openscad_workspace: workspace created at {modeling_dir}")
        return {
            "status": "ok",
            "workspace_dir": str(modeling_dir),
            "message": f"OpenSCAD workspace set up successfully at {modeling_dir}"
        }

    except Exception as e:
        logger.error(f"setup_openscad_workspace: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to set up OpenSCAD workspace: {str(e)}"
        }


async def generate_scad_code(project_name: str, design_specs: dict) -> dict:
    """Generate OpenSCAD code from design specifications.

    Args:
        project_name: Name of the project (non-empty string)
        design_specs: Design specifications dictionary (non-empty dict)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - scad_path: str (path to generated .scad file)
        - scad_content: str (the OpenSCAD code generated)
        - message: str
    """
    logger.info(f"generate_scad_code called: project={project_name}")

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("generate_scad_code: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    if not isinstance(design_specs, dict) or not design_specs:
        logger.warning("generate_scad_code: empty design_specs")
        return {
            "status": "error",
            "message": "design_specs must be a non-empty dictionary"
        }

    try:
        # Generate OpenSCAD code
        scad_code = _generate_basic_scad(project_name, design_specs)

        # Save to file
        scad_dir = _get_scad_dir(project_name)
        scad_path = scad_dir / "model.scad"

        with open(scad_path, "w") as f:
            f.write(scad_code)

        # Update metadata
        metadata = _load_modeling_metadata(project_name)
        model_record = {
            "id": str(uuid.uuid4()),
            "filename": "model.scad",
            "path": str(scad_path),
            "created_at": datetime.now().isoformat(),
            "status": "generated"
        }
        metadata["scad_models"].append(model_record)
        _save_modeling_metadata(project_name, metadata)

        logger.info(f"generate_scad_code: SCAD generated and saved to {scad_path}")
        return {
            "status": "ok",
            "scad_path": str(scad_path),
            "scad_content": scad_code,
            "message": f"OpenSCAD code generated successfully for {project_name}"
        }

    except Exception as e:
        logger.error(f"generate_scad_code: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate OpenSCAD code: {str(e)}"
        }


async def export_model(project_name: str, export_format: str = "stl", parts: Optional[list] = None) -> dict:
    """Export OpenSCAD model(s) to printable format.

    Args:
        project_name: Name of the project (non-empty string)
        export_format: Export format ("stl" or "3mf"), defaults to "stl"
        parts: Optional list of part names for multi-part export. If None, exports model.scad.
               If provided, exports each part as scad/{part_name}.scad

    Returns:
        dict with keys:
        - status: "ok", "pending", or "error"
        - export_path: str (path to exported file, for single-part)
        - export_paths: list[str] (paths to exported files, for multi-part)
        - export_format: str
        - parts: list[str] (part names, for multi-part success)
        - message: str
    """
    logger.info(f"export_model called: project={project_name}, format={export_format}, parts={parts}")

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("export_model: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    if export_format not in ["stl", "3mf"]:
        logger.warning(f"export_model: invalid export_format: {export_format}")
        return {
            "status": "error",
            "message": f"export_format must be 'stl' or '3mf', got '{export_format}'"
        }

    # Validate parts parameter
    if parts is not None:
        if not isinstance(parts, list) or len(parts) == 0:
            logger.warning("export_model: parts must be a non-empty list")
            return {
                "status": "error",
                "message": "parts must be a non-empty list of part names"
            }

    try:
        # Multi-part export
        if parts is not None:
            return await _export_multi_part(project_name, export_format, parts)
        # Single-part export
        else:
            return await _export_single_part(project_name, export_format)

    except Exception as e:
        logger.error(f"export_model: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to export model: {str(e)}"
        }


async def _export_single_part(project_name: str, export_format: str) -> dict:
    """Export single model.scad file.

    Args:
        project_name: Name of the project
        export_format: Export format ("stl" or "3mf")

    Returns:
        dict with export result
    """
    # Check if OpenSCAD binary exists
    if not os.path.exists(OPENSCAD_PATH):
        logger.warning(f"_export_single_part: OpenSCAD binary not found at {OPENSCAD_PATH}")
        return {
            "status": "pending",
            "export_format": export_format,
            "message": f"OpenSCAD binary not found at {OPENSCAD_PATH}. Model file is ready for manual rendering."
        }

    scad_dir = _get_scad_dir(project_name)
    scad_path = scad_dir / "model.scad"

    if not scad_path.exists():
        logger.warning(f"_export_single_part: SCAD file not found at {scad_path}")
        return {
            "status": "error",
            "message": f"OpenSCAD model not found at {scad_path}"
        }

    exports_dir = _get_exports_dir(project_name)
    output_file = exports_dir / f"model.{export_format}"

    try:
        cmd = [OPENSCAD_PATH, "-o", str(output_file), str(scad_path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        logger.info(f"_export_single_part: model exported to {output_file}")

        # Validate exported file
        if not _validate_export_file(output_file):
            logger.error(f"_export_single_part: exported file is empty or missing: {output_file}")
            return {
                "status": "error",
                "message": f"Exported file is empty or invalid at {output_file}"
            }

        # Update metadata
        metadata = _load_modeling_metadata(project_name)
        export_record = {
            "id": str(uuid.uuid4()),
            "filename": f"model.{export_format}",
            "format": export_format,
            "path": str(output_file),
            "created_at": datetime.now().isoformat(),
            "status": "exported"
        }
        metadata["exports"].append(export_record)
        _save_modeling_metadata(project_name, metadata)

        return {
            "status": "ok",
            "export_path": str(output_file),
            "export_format": export_format,
            "message": f"Model exported successfully to {export_format.upper()}"
        }

    except subprocess.TimeoutExpired:
        logger.error(f"_export_single_part: OpenSCAD timeout for {project_name}")
        return {
            "status": "error",
            "message": "OpenSCAD export timed out (>300 seconds)"
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"_export_single_part: OpenSCAD failed: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        return {
            "status": "error",
            "message": f"OpenSCAD export failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
        }


async def _export_multi_part(project_name: str, export_format: str, parts: list) -> dict:
    """Export multiple SCAD files as separate parts.

    Args:
        project_name: Name of the project
        export_format: Export format ("stl" or "3mf")
        parts: List of part names to export

    Returns:
        dict with export result
    """
    # Check if OpenSCAD binary exists
    if not os.path.exists(OPENSCAD_PATH):
        logger.warning(f"_export_multi_part: OpenSCAD binary not found at {OPENSCAD_PATH}")
        return {
            "status": "pending",
            "export_format": export_format,
            "message": f"OpenSCAD binary not found at {OPENSCAD_PATH}. Part files are ready for manual rendering."
        }

    scad_dir = _get_scad_dir(project_name)
    exports_dir = _get_exports_dir(project_name)

    # Validate all SCAD files exist before exporting
    missing_parts = []
    for part_name in parts:
        part_scad = scad_dir / f"{part_name}.scad"
        if not part_scad.exists():
            missing_parts.append(part_name)

    if missing_parts:
        logger.warning(f"_export_multi_part: missing SCAD files for parts: {missing_parts}")
        return {
            "status": "error",
            "message": f"SCAD files not found for parts: {', '.join(missing_parts)}"
        }

    export_paths = []
    failed_parts = []

    # Export each part
    for part_name in parts:
        part_scad = scad_dir / f"{part_name}.scad"
        output_file = exports_dir / f"{part_name}.{export_format}"

        try:
            cmd = [OPENSCAD_PATH, "-o", str(output_file), str(part_scad)]
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
            logger.info(f"_export_multi_part: part '{part_name}' exported to {output_file}")

            # Validate exported file
            if not _validate_export_file(output_file):
                logger.warning(f"_export_multi_part: exported file is empty for part '{part_name}'")
                failed_parts.append(part_name)
                continue

            export_paths.append(str(output_file))

        except subprocess.TimeoutExpired:
            logger.warning(f"_export_multi_part: timeout exporting part '{part_name}'")
            failed_parts.append(part_name)
        except subprocess.CalledProcessError as e:
            logger.warning(f"_export_multi_part: failed to export part '{part_name}': {e.stderr.decode() if e.stderr else 'Unknown error'}")
            failed_parts.append(part_name)

    # Check if any exports succeeded
    if not export_paths:
        logger.error(f"_export_multi_part: no parts exported successfully for {project_name}")
        return {
            "status": "error",
            "message": f"Failed to export any parts: {', '.join(failed_parts)}"
        }

    # If some parts failed, return warning
    if failed_parts:
        logger.warning(f"_export_multi_part: partial success for {project_name} (failed: {failed_parts})")
        message = f"Exported {len(export_paths)} of {len(parts)} parts successfully. Failed: {', '.join(failed_parts)}"
        status = "ok"
    else:
        message = f"All {len(parts)} parts exported successfully to {export_format.upper()}"
        status = "ok"

    # Update metadata with multi-part record
    metadata = _load_modeling_metadata(project_name)
    export_record = {
        "id": str(uuid.uuid4()),
        "type": "multi_part",
        "parts": [p for p in parts if p not in failed_parts],
        "format": export_format,
        "paths": export_paths,
        "created_at": datetime.now().isoformat(),
        "status": "exported"
    }
    metadata["exports"].append(export_record)
    _save_modeling_metadata(project_name, metadata)

    return {
        "status": status,
        "export_paths": export_paths,
        "export_format": export_format,
        "parts": [p for p in parts if p not in failed_parts],
        "message": message
    }
