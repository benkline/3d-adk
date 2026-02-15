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


def _get_previews_dir(project_name: str) -> Path:
    """Get the path to the previews subdirectory for a project."""
    previews_dir = _get_modeling_dir(project_name) / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    return previews_dir


def _get_camera_params(perspective: str) -> str:
    """Get OpenSCAD camera parameters for a given perspective view.

    Args:
        perspective: View angle name (front, back, left, right, top, bottom, isometric)

    Returns:
        Camera parameter string for OpenSCAD --camera flag
    """
    camera_map = {
        "isometric": "0,0,0,55,0,25,140",
        "front": "0,0,0,0,0,0,200",
        "back": "0,0,0,0,180,0,200",
        "left": "0,0,0,0,270,0,200",
        "right": "0,0,0,0,90,0,200",
        "top": "0,0,0,90,0,0,200",
        "bottom": "0,0,0,-90,0,0,200"
    }
    # Return requested perspective or default to isometric
    return camera_map.get(perspective.lower(), camera_map["isometric"])


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


def _extract_scad_params(design_specs: dict) -> dict:
    """Extract all SCAD-relevant parameters from design specifications.

    Returns a flat dict with all parameters needed for code generation.
    """
    specs = design_specs.get("specifications", {})
    dims = specs.get("overall_dimensions", {})
    design_brief = design_specs.get("design_brief", {})

    width = float(dims.get("width", 100))
    height = float(dims.get("height", 80))
    depth = float(dims.get("depth", 60))
    wall_thickness = float(specs.get("wall_thickness_mm", 2))
    material = specs.get("material", "PLA")
    infill_percentage = float(specs.get("infill_percentage", 20))
    print_orientation = specs.get("print_orientation", "flat")
    tolerance = float(dims.get("tolerance_mm", 0.2)) if "tolerance_mm" in dims else 0.2
    supports_required = specs.get("supports_required", False)

    # Extract from design_brief if available
    object_name = design_brief.get("name", "object")
    aesthetics = design_brief.get("aesthetics", "functional")

    # Extract parts (if available)
    parts = design_specs.get("parts", [])
    if not parts:
        # Create a single default part
        parts = [{
            "name": "main_body",
            "quantity": 1,
            "dimensions": dims,
            "tolerance_mm": tolerance
        }]

    return {
        "width": width,
        "height": height,
        "depth": depth,
        "wall_thickness": wall_thickness,
        "material": material,
        "infill_percentage": infill_percentage,
        "print_orientation": print_orientation,
        "tolerance": tolerance,
        "supports_required": supports_required,
        "object_name": object_name,
        "aesthetics": aesthetics,
        "parts": parts
    }


def _sanitize_scad_identifier(name: str) -> str:
    """Convert a name into a valid OpenSCAD identifier."""
    # Replace spaces and hyphens with underscores
    name = name.replace(" ", "_").replace("-", "_")
    # Keep only alphanumeric and underscores
    name = "".join(c for c in name if c.isalnum() or c == "_")
    # Ensure it doesn't start with a number
    if name and name[0].isdigit():
        name = "_" + name
    return name.lower()


def _render_scad_header(project_name: str, params: dict) -> str:
    """Generate OpenSCAD file header with metadata."""
    from datetime import datetime
    timestamp = datetime.now().isoformat()

    header = f"""// 3D-ADK Generated Model
// Project: {project_name}
// Generated: {timestamp}
// Material: {params["material"]}
// Object: {params["object_name"]}
// Aesthetics: {params["aesthetics"]}

"""
    return header


def _render_parameters_block(params: dict) -> str:
    """Generate the PARAMETERS section with OpenSCAD variables."""
    block = """// === PARAMETERS ===
$fn = 100;  // Fragment resolution for smooth curves
wall_thickness = {wall};
tolerance = {tol};
infill_percentage = {infill};

""".format(
        wall=params["wall_thickness"],
        tol=params["tolerance"],
        infill=params["infill_percentage"]
    )
    return block


def _render_dimensions_block(params: dict) -> str:
    """Generate the DIMENSIONS section with named dimension variables."""
    block = """// === DIMENSIONS ===
width = {width};
height = {height};
depth = {depth};

""".format(
        width=params["width"],
        height=params["height"],
        depth=params["depth"]
    )
    return block


def _render_module_for_part(part: dict, params: dict) -> str:
    """Generate an OpenSCAD module for a single part.

    Creates a hollow box with walls using difference().
    """
    part_name = _sanitize_scad_identifier(part.get("name", "part"))
    wall = params["wall_thickness"]

    # Get part-specific dimensions if available
    part_dims = part.get("dimensions", {})
    part_width = float(part_dims.get("width", params["width"]))
    part_height = float(part_dims.get("height", params["height"]))
    part_depth = float(part_dims.get("depth", params["depth"]))

    module_code = f"""module {part_name}(w={part_width}, h={part_height}, d={part_depth}, wall={wall}) {{
  difference() {{
    cube([w, h, d]);
    translate([wall, wall, wall])
      cube([w-2*wall, h-2*wall, d-wall]);
  }}
}}

"""
    return module_code


def _render_assembly_block(parts: list, params: dict) -> str:
    """Generate the ASSEMBLY section that instantiates all modules."""
    block = "// === ASSEMBLY ===\n"

    z_offset = 0
    for i, part in enumerate(parts):
        part_name = _sanitize_scad_identifier(part.get("name", "part"))
        quantity = part.get("quantity", 1)

        if quantity == 1:
            # Single instance
            if i == 0:
                block += f"{part_name}();\n"
            else:
                block += f"translate([0, 0, {z_offset}]) {part_name}();\n"
        else:
            # Multiple instances stacked
            for q in range(quantity):
                offset = z_offset + (q * params["depth"])
                block += f"translate([0, 0, {offset}]) {part_name}();\n"

        z_offset += params["depth"]

    return block + "\n"


def _generate_comprehensive_scad(project_name: str, design_specs: dict) -> str:
    """Generate comprehensive, well-structured OpenSCAD code from design specifications.

    Produces code with clear sections: PARAMETERS, DIMENSIONS, MODULES, ASSEMBLY.
    Returns the complete OpenSCAD code as a string.
    """
    try:
        # Extract all parameters
        params = _extract_scad_params(design_specs)

        # Build the complete SCAD file
        scad_code = (
            _render_scad_header(project_name, params) +
            _render_parameters_block(params) +
            _render_dimensions_block(params) +
            "// === MODULES ===\n"
        )

        # Add a module for each part
        for part in params["parts"]:
            scad_code += _render_module_for_part(part, params)

        # Add assembly section
        scad_code += _render_assembly_block(params["parts"], params)

        return scad_code

    except Exception as e:
        logger.error(f"Error in _generate_comprehensive_scad: {str(e)}", exc_info=True)
        raise


def _save_part_scad_files(project_name: str, parts: list, params: dict) -> list:
    """Save individual OpenSCAD files for each part in a multi-part design.

    Returns a list of paths to the generated part files.
    """
    part_files = []

    for part in parts:
        part_name = _sanitize_scad_identifier(part.get("name", "part"))

        # Create per-part SCAD code
        scad_dir = _get_scad_dir(project_name)
        part_file = scad_dir / f"{part_name}.scad"

        # Generate header + parameters + dimensions + this part's module
        part_code = (
            _render_scad_header(f"{project_name}_{part_name}", params) +
            _render_parameters_block(params) +
            _render_dimensions_block(params) +
            "// === MODULE ===\n" +
            _render_module_for_part(part, params)
        )

        with open(part_file, "w") as f:
            f.write(part_code)

        part_files.append(str(part_file))

    return part_files


def _generate_basic_scad(project_name: str, design_specs: dict) -> str:
    """Generate comprehensive OpenSCAD code from design specifications.

    Attempts to use solidpython2 if available, falls back to string generation.
    Returns the OpenSCAD code as a string.
    """
    try:
        # Try comprehensive generation first
        return _generate_comprehensive_scad(project_name, design_specs)
    except Exception as e:
        logger.warning(f"Comprehensive SCAD generation failed: {str(e)}, using fallback")
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
        - part_files: list[str] (if multi-part design)
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

        # Check if multi-part design
        parts = design_specs.get("parts", [])
        part_files = []
        if parts and len(parts) > 1:
            # Save individual part files
            params = _extract_scad_params(design_specs)
            part_files = _save_part_scad_files(project_name, parts, params)

        # Update metadata
        metadata = _load_modeling_metadata(project_name)
        model_record = {
            "id": f"model_{uuid.uuid4().hex[:8]}",
            "filename": "model.scad",
            "path": str(scad_path),
            "created_at": datetime.now().isoformat(),
            "status": "generated",
            "part_count": len(parts) if parts else 1,
            "part_files": part_files
        }
        metadata["scad_models"].append(model_record)
        _save_modeling_metadata(project_name, metadata)

        logger.info(f"generate_scad_code: SCAD generated and saved to {scad_path}")
        result = {
            "status": "ok",
            "scad_path": str(scad_path),
            "scad_content": scad_code,
            "message": f"OpenSCAD code generated successfully for {project_name}"
        }
        if part_files:
            result["part_files"] = part_files
        return result

    except Exception as e:
        logger.error(f"generate_scad_code: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate OpenSCAD code: {str(e)}"
        }


async def export_model(project_name: str, export_format: str = "stl") -> dict:
    """Export OpenSCAD model to printable format.

    Args:
        project_name: Name of the project (non-empty string)
        export_format: Export format ("stl" or "3mf"), defaults to "stl"

    Returns:
        dict with keys:
        - status: "ok", "pending", or "error"
        - export_path: str (path to exported file, if generated)
        - export_format: str
        - message: str
    """
    logger.info(f"export_model called: project={project_name}, format={export_format}")

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

    try:
        # Check if SCAD file exists
        scad_dir = _get_scad_dir(project_name)
        scad_path = scad_dir / "model.scad"

        if not scad_path.exists():
            logger.warning(f"export_model: SCAD file not found at {scad_path}")
            return {
                "status": "error",
                "message": f"OpenSCAD model not found at {scad_path}"
            }

        # Check if OpenSCAD binary exists
        if not os.path.exists(OPENSCAD_PATH):
            logger.warning(f"export_model: OpenSCAD binary not found at {OPENSCAD_PATH}")
            return {
                "status": "pending",
                "export_format": export_format,
                "message": f"OpenSCAD binary not found at {OPENSCAD_PATH}. Model file generated but export is pending manual rendering."
            }

        # Determine output file name
        exports_dir = _get_exports_dir(project_name)
        output_file = exports_dir / f"model.{export_format}"

        # Run OpenSCAD to export
        try:
            cmd = [OPENSCAD_PATH, "-o", str(output_file), str(scad_path)]
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
            logger.info(f"export_model: model exported to {output_file}")

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
            logger.error(f"export_model: OpenSCAD timeout for {project_name}")
            return {
                "status": "error",
                "message": "OpenSCAD export timed out (>300 seconds)"
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"export_model: OpenSCAD failed: {e.stderr.decode()}")
            return {
                "status": "error",
                "message": f"OpenSCAD export failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
            }

    except Exception as e:
        logger.error(f"export_model: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to export model: {str(e)}"
        }


async def render_preview(
    project_name: str,
    perspectives: Optional[list] = None,
    resolution: int = 512
) -> dict:
    """Generate preview images of OpenSCAD model from multiple viewing angles.

    Args:
        project_name: Name of the project (non-empty string)
        perspectives: List of view angles to render (front, back, left, right, top, bottom, isometric).
                     Defaults to ["front", "isometric", "top"]
        resolution: Output resolution in pixels (256-1024), defaults to 512

    Returns:
        dict with keys:
        - status: "ok", "pending", or "error"
        - preview_paths: list[str] (if status is "ok")
        - perspectives: list[str] (if status is "ok")
        - resolution: int (if status is "ok")
        - message: str
    """
    logger.info(f"render_preview called: project={project_name}, resolution={resolution}")

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("render_preview: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    # Validate and normalize resolution
    if not isinstance(resolution, int) or resolution < 256 or resolution > 1024:
        logger.warning(f"render_preview: invalid resolution: {resolution}")
        return {
            "status": "error",
            "message": "resolution must be an integer between 256 and 1024"
        }

    # Set default perspectives if not provided
    if perspectives is None:
        perspectives = ["front", "isometric", "top"]

    # Validate perspective list
    if not isinstance(perspectives, list) or not perspectives:
        logger.warning("render_preview: invalid perspectives list")
        return {
            "status": "error",
            "message": "perspectives must be a non-empty list"
        }

    # Validate each perspective name
    valid_perspectives = {"front", "back", "left", "right", "top", "bottom", "isometric"}
    invalid = [p for p in perspectives if p not in valid_perspectives]
    if invalid:
        logger.warning(f"render_preview: invalid perspective names: {invalid}")
        return {
            "status": "error",
            "message": f"Invalid perspective names: {', '.join(invalid)}. Valid options: {', '.join(sorted(valid_perspectives))}"
        }

    try:
        # Check if SCAD file exists
        scad_dir = _get_scad_dir(project_name)
        scad_path = scad_dir / "model.scad"

        if not scad_path.exists():
            logger.warning(f"render_preview: SCAD file not found at {scad_path}")
            return {
                "status": "error",
                "message": f"OpenSCAD model not found at {scad_path}"
            }

        # Check if OpenSCAD binary exists
        if not os.path.exists(OPENSCAD_PATH):
            logger.warning(f"render_preview: OpenSCAD binary not found at {OPENSCAD_PATH}")
            return {
                "status": "pending",
                "message": f"OpenSCAD binary not found at {OPENSCAD_PATH}. Model file ready but preview rendering is pending."
            }

        # Generate previews for each perspective
        previews_dir = _get_previews_dir(project_name)
        preview_paths = []
        successful_perspectives = []

        for perspective in perspectives:
            try:
                camera_params = _get_camera_params(perspective)
                output_file = previews_dir / f"preview_{perspective}.png"

                # Run OpenSCAD to generate preview
                cmd = [
                    OPENSCAD_PATH,
                    "-o", str(output_file),
                    "--imgsize=" + str(resolution) + "," + str(resolution),
                    "--camera=" + camera_params,
                    str(scad_path)
                ]

                subprocess.run(cmd, check=True, capture_output=True, timeout=120)
                logger.info(f"render_preview: generated {perspective} preview at {output_file}")
                preview_paths.append(str(output_file))
                successful_perspectives.append(perspective)

            except subprocess.TimeoutExpired:
                logger.warning(f"render_preview: timeout rendering {perspective} for {project_name}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"render_preview: failed to render {perspective}: {e.stderr.decode() if e.stderr else 'Unknown error'}")
            except Exception as e:
                logger.warning(f"render_preview: error rendering {perspective}: {str(e)}")

        # Check if any previews were generated
        if not preview_paths:
            logger.error(f"render_preview: no previews generated for {project_name}")
            return {
                "status": "error",
                "message": f"Failed to generate any preview images for {project_name}"
            }

        # Update metadata
        metadata = _load_modeling_metadata(project_name)
        preview_record = {
            "id": f"preview_{uuid.uuid4().hex[:8]}",
            "perspectives": successful_perspectives,
            "resolution": resolution,
            "paths": preview_paths,
            "created_at": datetime.now().isoformat(),
            "status": "generated"
        }

        if "previews" not in metadata:
            metadata["previews"] = []
        metadata["previews"].append(preview_record)
        _save_modeling_metadata(project_name, metadata)

        return {
            "status": "ok",
            "preview_paths": preview_paths,
            "perspectives": successful_perspectives,
            "resolution": resolution,
            "message": f"Generated {len(preview_paths)} preview image(s) for {project_name}"
        }

    except Exception as e:
        logger.error(f"render_preview: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to render previews: {str(e)}"
        }
