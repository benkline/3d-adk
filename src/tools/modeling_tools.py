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


# Material-specific minimum wall thickness constants
_WALL_THICKNESS_MINIMUMS = {
    "PLA": 1.2,
    "PETG": 1.5,
    "ABS": 1.5,
    "TPU": 0.8,
    "Resin": 0.5,
    "Nylon": 1.5,
}
_DEFAULT_WALL_MIN = 1.2  # mm


def _analyze_wall_thickness(specs: dict) -> tuple[bool, list]:
    """Check wall thickness against material minimums.

    Args:
        specs: Design specifications dict

    Returns:
        Tuple of (ok: bool, warnings: list[str])
    """
    wall_thickness = specs.get("specifications", {}).get("wall_thickness_mm", _DEFAULT_WALL_MIN)
    material = specs.get("specifications", {}).get("material", "PLA")

    min_thickness = _WALL_THICKNESS_MINIMUMS.get(material, _DEFAULT_WALL_MIN)
    warnings = []

    if wall_thickness < min_thickness:
        ok = False
        warnings.append(
            f"Wall thickness {wall_thickness}mm is below minimum {min_thickness}mm for {material}"
        )
    else:
        ok = True

    return ok, warnings


def _analyze_overhangs(specs: dict) -> tuple[bool, list, list]:
    """Detect potential overhang issues.

    Args:
        specs: Design specifications dict

    Returns:
        Tuple of (overhang_ok: bool, warnings: list[str], suggestions: list[str])
    """
    specs_data = specs.get("specifications", {})
    supports_required = specs_data.get("supports_required", False)
    print_orientation = specs_data.get("print_orientation", "flat")
    dims = specs_data.get("overall_dimensions", {})

    warnings = []
    suggestions = []

    # Check if supports are explicitly required
    if supports_required:
        overhang_ok = False
        warnings.append("Model requires support structures")
        suggestions.append("Use tree supports for better surface quality and reduced material waste")
        suggestions.append(f"Consider rotating orientation from '{print_orientation}' for reduced supports")
    else:
        # Check for potential overhangs based on dimensions
        width = float(dims.get("width", 100))
        height = float(dims.get("height", 80))
        depth = float(dims.get("depth", 60))

        # If height is significantly larger than width, there may be overhangs
        max_horizontal = max(width, depth)
        if height > max_horizontal * 2:
            overhang_ok = False
            warnings.append(f"Height ({height}mm) is significantly larger than horizontal dimensions ({max_horizontal}mm), potential overhangs detected")
            suggestions.append(f"Consider different print orientation or adding bracing")
        else:
            overhang_ok = True

    return overhang_ok, warnings, suggestions


def _analyze_hollow_sections(specs: dict) -> list:
    """Check infill and structure for hollow section concerns.

    Args:
        specs: Design specifications dict

    Returns:
        List of warning strings
    """
    specs_data = specs.get("specifications", {})
    infill = specs_data.get("infill_percentage", 20)
    constraints = specs.get("design_brief", {}).get("constraints", [])

    warnings = []

    if infill < 10:
        warnings.append(
            f"Very low infill ({infill}%) may cause structural weakness and layer separation"
        )
    elif infill < 20:
        # Check if structural strength is mentioned in constraints
        constraint_str = " ".join(constraints).lower()
        if any(word in constraint_str for word in ["structural", "load", "strength", "support"]):
            warnings.append(
                f"Low infill ({infill}%) with structural requirements; consider increasing to 20%+"
            )

    return warnings


def _build_printability_report(specs: dict) -> dict:
    """Assemble complete printability report from spec analysis.

    Args:
        specs: Design specifications dict

    Returns:
        Printability report dict
    """
    # Analyze each aspect
    wall_ok, wall_warnings = _analyze_wall_thickness(specs)
    overhang_ok, overhang_warnings, overhang_suggestions = _analyze_overhangs(specs)
    hollow_warnings = _analyze_hollow_sections(specs)

    # Check multi-part assembly tolerances
    parts = specs.get("parts", [])
    assemblies_ok = True
    if len(parts) > 1:
        for part in parts:
            tolerance = part.get("tolerance_mm", 0.2)
            if tolerance < 0.1:
                assemblies_ok = False
                break

    # Combine all warnings and suggestions
    all_warnings = wall_warnings + overhang_warnings + hollow_warnings
    all_suggestions = overhang_suggestions

    # Feasibility: primarily based on wall thickness (most critical)
    feasible = wall_ok and (len(all_warnings) == 0 or not wall_ok)  # Always show warnings but feasible if wall is ok
    feasible = wall_ok  # Actually: it's feasible if walls are ok, even with warnings

    # Get estimates from specs
    specs_data = specs.get("specifications", {})
    print_hours = float(specs_data.get("estimated_print_time_hours", 0))
    weight_g = float(specs_data.get("estimated_weight_g", 0))

    return {
        "feasible": feasible,
        "wall_thickness_ok": wall_ok,
        "overhang_ok": overhang_ok,
        "assemblies_ok": assemblies_ok,
        "warnings": all_warnings,
        "suggestions": all_suggestions,
        "estimates": {
            "print_hours": print_hours,
            "weight_g": weight_g,
        }
    }


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


async def analyze_printability(project_name: str, specs_path: Optional[str] = None) -> dict:
    """Analyze design specifications for 3D printability.

    Args:
        project_name: Name of the project (non-empty string)
        specs_path: Optional path to design_specs.json (defaults to design/design_specs.json)

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - report: dict (if status is "ok") with printability analysis
        - message: str
    """
    logger.info(f"analyze_printability called: project={project_name}")

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("analyze_printability: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    try:
        # Load design specs
        design_specs = _load_design_specs(project_name, specs_path)

        # Build printability report
        report = _build_printability_report(design_specs)

        # Update metadata
        metadata = _load_modeling_metadata(project_name)
        analysis_record = {
            "id": f"analysis_{uuid.uuid4().hex[:8]}",
            "created_at": datetime.now().isoformat(),
            "status": "analyzed",
            "report": report
        }
        if "printability_reports" not in metadata:
            metadata["printability_reports"] = []
        metadata["printability_reports"].append(analysis_record)
        _save_modeling_metadata(project_name, metadata)

        logger.info(f"analyze_printability: analysis complete for {project_name}")
        return {
            "status": "ok",
            "report": report,
            "message": f"Printability analysis complete for {project_name}"
        }

    except FileNotFoundError as e:
        logger.error(f"analyze_printability: file not found: {str(e)}")
        return {
            "status": "error",
            "message": f"Design specs file not found: {str(e)}"
        }
    except json.JSONDecodeError as e:
        logger.error(f"analyze_printability: invalid JSON: {str(e)}")
        return {
            "status": "error",
            "message": f"Design specs file contains invalid JSON: {str(e)}"
        }
    except Exception as e:
        logger.error(f"analyze_printability: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to analyze printability: {str(e)}"
        }


def _optimize_orientation(params: dict) -> tuple[str, str]:
    """Determine optimal print orientation based on dimensions.

    Strategy: Minimize print height to reduce print time and supports.
    The smallest dimension should be the print height; the other two form the base.

    Returns: (orientation, rationale)
    - "flat": width×depth base, height as print height
    - "upright": depth×height base, width as print height
    - "side": width×height base, depth as print height
    """
    width = params["width"]
    height = params["height"]
    depth = params["depth"]

    # Calculate print height for each orientation
    orientations = {
        "flat": (width * depth, height),        # (bed_area, print_height)
        "upright": (depth * height, width),     # (bed_area, print_height)
        "side": (width * height, depth)         # (bed_area, print_height)
    }

    # Choose orientation with the SMALLEST print height (minimize time)
    # Tiebreaker: largest bed area for better support adhesion
    best_orientation = min(orientations.items(),
                          key=lambda x: (x[1][1], -x[1][0]))[0]

    bed_area, print_height = orientations[best_orientation]
    rationale = f"Orientation optimized: {best_orientation.upper()} ({print_height:.0f}mm height, {bed_area:.0f}mm² bed area)"

    return best_orientation, rationale


def _recommend_infill(params: dict) -> tuple[int, str]:
    """Recommend infill percentage based on constraints and use case.

    Returns: (infill_percentage, rationale)
    """
    constraints = params.get("constraints", [])
    constraint_str = " ".join(constraints).lower() if constraints else ""

    # Tiers based on functional requirements
    if "structural" in constraint_str or "load" in constraint_str or "stress" in constraint_str:
        infill = 50
        rationale = "50% infill recommended for structural/load-bearing parts"
    elif "functional" in constraint_str or "mechanical" in constraint_str:
        infill = 35
        rationale = "35% infill recommended for functional/mechanical parts"
    elif "decorative" in constraint_str or "display" in constraint_str:
        infill = 10
        rationale = "10% infill recommended for decorative/display parts"
    else:
        # Standard default
        infill = 20
        rationale = "20% infill recommended for standard parts"

    return infill, rationale


def _determine_support_strategy(params: dict, printability_report: Optional[dict] = None) -> tuple[bool, str, str]:
    """Determine support material requirements.

    Returns: (supports_required, support_type, rationale)
    """
    # If printability report is provided, check for overhang warnings
    if printability_report and "warnings" in printability_report:
        warnings = printability_report.get("warnings", [])
        if any("overhang" in w.lower() for w in warnings):
            return True, "touching_buildplate", "Based on printability analysis: overhangs detected"

    # Heuristic: parts that are tall and narrow likely need supports
    width = params["width"]
    height = params["height"]
    depth = params["depth"]

    # Aspect ratio check: if height > 2 * min(width, depth), might need supports
    min_base = min(width, depth)
    aspect_ratio = height / min_base if min_base > 0 else 1

    if aspect_ratio > 2.5:
        return True, "tree", "Tall narrow geometry: tree supports recommended for stability"
    else:
        return False, "none", "Part geometry suitable for support-free printing"


def _estimate_weight(params: dict, infill_pct: float, orientation: str) -> float:
    """Estimate print weight in grams.

    Calculates volume with wall thickness, applies density and infill factor.
    """
    width = params["width"]
    height = params["height"]
    depth = params["depth"]
    wall = params.get("wall_thickness", 2)
    material = params.get("material", "PLA")

    # Material densities (g/cm³)
    densities = {
        "PLA": 1.24,
        "PETG": 1.27,
        "ABS": 1.05,
        "Resin": 1.2,
        "Nylon": 1.14
    }
    density = densities.get(material, 1.24)

    # Volume calculation: outer box minus hollow interior
    outer_volume = (width * height * depth) / 1000  # Convert mm³ to cm³

    # Inner hollow volume (walls always solid)
    inner_dims = [width - 2*wall, height - 2*wall, depth - 2*wall]
    if all(d > 0 for d in inner_dims):
        inner_volume = (inner_dims[0] * inner_dims[1] * inner_dims[2]) / 1000
    else:
        inner_volume = 0

    # Wall volume (always solid)
    wall_volume = outer_volume - inner_volume

    # Hollow interior with infill
    hollow_volume = inner_volume

    # Weight = wall_volume (solid) + hollow_volume * (infill_percentage / 100)
    total_volume = wall_volume + (hollow_volume * infill_pct / 100)
    weight_g = total_volume * density

    return round(weight_g, 1)


def _estimate_print_time(weight_g: float, params: dict, infill_pct: float) -> float:
    """Estimate print time in hours.

    Base formula: weight / 8 grams per hour (slower than design's simplistic /10).
    Adjusted for infill and supports.
    """
    # Base print speed assumption: 8g per hour
    base_hours = weight_g / 8.0

    # Infill adjustment: higher infill = slightly more time (but not linear)
    infill_factor = 0.7 + (infill_pct / 100 * 0.3)  # Range: 0.7 to 1.0

    # Adjust for support overhead (if needed)
    has_supports = params.get("supports_required", False)
    support_factor = 1.2 if has_supports else 1.0

    total_hours = base_hours * infill_factor * support_factor

    return round(total_hours, 2)


def _estimate_cost(weight_g: float) -> str:
    """Estimate material cost in USD.

    Uses FILAMENT_COST_PER_KG from config.
    """
    from src.config import FILAMENT_COST_PER_KG

    cost = (weight_g / 1000) * FILAMENT_COST_PER_KG
    return f"${cost:.2f}"


async def optimize_parameters(
    project_name: str,
    specs_path: Optional[str] = None,
    printability_report: Optional[dict] = None
) -> dict:
    """Optimize model parameters for printing (orientation, infill, supports, time, cost).

    Args:
        project_name: Name of the project (non-empty string)
        specs_path: Optional path to design_specs.json (defaults to design/design_specs.json)
        printability_report: Optional dict from printability analysis (TICKET-013)
                            containing warnings and suggestions

    Returns:
        dict with keys:
        - status: "ok" or "error"
        - project_name: str (if ok)
        - recommendations: dict with optimization results (if ok)
        - message: str
    """
    logger.info(f"optimize_parameters called: project={project_name}")

    # Validate inputs
    if not isinstance(project_name, str) or not project_name.strip():
        logger.warning("optimize_parameters: empty project_name")
        return {
            "status": "error",
            "message": "project_name must be a non-empty string"
        }

    try:
        # Load design specs
        design_specs = _load_design_specs(project_name, specs_path)
        params = _extract_scad_params(design_specs)

        # Add constraints early (needed for infill recommendations)
        params["constraints"] = design_specs.get("design_brief", {}).get("constraints", [])

        # Get optimization recommendations
        orientation, orientation_rationale = _optimize_orientation(params)
        infill_pct, infill_rationale = _recommend_infill(params)
        supports_needed, support_type, support_rationale = _determine_support_strategy(
            params, printability_report
        )

        # Update params for weight/time calculations
        params["supports_required"] = supports_needed

        # Calculate estimates
        weight_g = _estimate_weight(params, infill_pct, orientation)
        print_time_hours = _estimate_print_time(weight_g, params, infill_pct)
        material_cost = _estimate_cost(weight_g)

        logger.info(f"optimize_parameters: optimization complete for {project_name}")

        return {
            "status": "ok",
            "project_name": project_name,
            "recommendations": {
                "print_orientation": orientation,
                "orientation_rationale": orientation_rationale,
                "infill_percentage": infill_pct,
                "infill_rationale": infill_rationale,
                "supports_required": supports_needed,
                "support_type": support_type,
                "support_rationale": support_rationale,
                "estimated_weight_g": weight_g,
                "estimated_print_time_hours": print_time_hours,
                "estimated_material_cost_usd": material_cost
            },
            "message": "Parameter optimization complete"
        }

    except FileNotFoundError as e:
        logger.error(f"optimize_parameters: file not found: {str(e)}")
        return {
            "status": "error",
            "message": f"Design specs file not found: {str(e)}"
        }
    except json.JSONDecodeError as e:
        logger.error(f"optimize_parameters: invalid JSON: {str(e)}")
        return {
            "status": "error",
            "message": f"Design specs file contains invalid JSON: {str(e)}"
        }
    except Exception as e:
        logger.error(f"optimize_parameters: error for {project_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to optimize parameters: {str(e)}"
        }
