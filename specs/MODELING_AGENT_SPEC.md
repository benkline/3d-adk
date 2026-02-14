# 3D-ADK Modeling Phase Agent Specification

## Overview
Converts approved designs into ready-to-print 3D CAD models using OpenSCAD.

## Core Responsibilities

### 1. Design Input Processing
Receive and validate design specifications from Design Phase Agent.

**Input Validation:**
- Verify blueprint completeness
- Check dimension feasibility
- Validate material compatibility
- Ensure specifications are unambiguous

**Processing:**
- Parse design specifications JSON
- Extract dimension and tolerance data
- Identify part assemblies
- Create modeling workspace
- Generate modeling checklist

**Output:**
```json
{
  "model_config": {
    "project_id": "uuid",
    "parts": [...],
    "total_dimensions": {...},
    "print_constraints": {...}
  }
}
```

### 2. OpenSCAD Model Generation
Create parametric 3D models suitable for 3D printing.

**Process:**
- Generate OpenSCAD code from design specs
- Build modular structure for multi-part models
- Use parametric design for easy modifications
- Apply wall thickness and tolerance specifications
- Create appropriate geometries for each part

**Code Generation Strategy:**
- Use Python to generate OpenSCAD scripts
- Include comprehensive comments
- Create parameter block at top of file
- Use modules for reusable components
- Generate both full model and individual part modules

**Example Structure:**
```scad
// 3D-ADK Generated Model
// Project: [name]
// Date: [timestamp]

// === PARAMETERS ===
$fn = 100; // Fragment resolution
wall_thickness = 2;
material = "PLA";
tolerance = 0.5;

// === DIMENSIONS ===
width = 100;
height = 80;
depth = 60;

// === MODULES ===
module body() {
  // Body geometry
}

module lid() {
  // Lid geometry
}

// === ASSEMBLY ===
body();
translate([0, 0, height]) lid();
```

**Output:**
- Main assembly `.scad` file
- Individual part `.scad` files
- Documented parameter block

### 3. Model Refinement
Optimize and validate the model for printability.

**Validation Checks:**
- Model wall thickness >= specified minimum
- No internal voids that trap support material
- Proper tolerance stack-up for assemblies
- Overhangs <= 45 degrees (or support needed)
- Model dimensions match specifications

**Optimization:**
- Smooth curves with appropriate resolution
- Minimize model complexity where possible
- Suggest infill percentage based on part function
- Recommend print orientation for strength
- Calculate support material needs

**Printability Analysis:**
```json
{
  "printability": {
    "feasible": boolean,
    "wall_thickness_ok": boolean,
    "overhang_ok": boolean,
    "assemblies_ok": boolean,
    "warnings": ["..."],
    "suggestions": ["..."],
    "estimated_print_time_hours": number,
    "estimated_weight_g": number
  }
}
```

### 4. Export & File Preparation
Generate ready-to-print files in multiple formats.

**Export Formats:**
- **STL (ASCII & Binary)**: Standard for slicers
- **3MF**: Modern format with metadata support
- **OpenSCAD Script**: Source for future modifications

**Export Process:**
1. Generate STL from OpenSCAD model
2. Apply print orientation optimizations
3. Generate preview images
4. Create separate part files if multi-part
5. Document export parameters

**Exported Files:**
```
model/
├── project.scad (source)
├── preview_front.png
├── preview_iso.png
├── exports/
│   ├── project_final.stl
│   ├── project_final.3mf
│   ├── part_1.stl (if multi-part)
│   ├── part_2.stl (if multi-part)
│   └── model_metadata.json
```

## OpenSCAD Integration

### Generation Tools
- Use `openscad` CLI for rendering
- Use Python STL libraries for conversion if needed
- Generate preview images via OpenSCAD rendering

### Supported Primitives
- Cubes, spheres, cylinders, polyhedra
- 2D shapes with extrusion
- Boolean operations (union, difference, intersection)
- Linear/rotational arrays
- Parametric transformations

## Model Metadata

Store comprehensive model information:

```json
{
  "model_metadata": {
    "project_id": "uuid",
    "project_name": "string",
    "created_at": "timestamp",
    "design_source": "string",
    "openscad_version": "string",

    "specifications": {
      "overall_dimensions": {...},
      "wall_thickness_mm": number,
      "infill_percentage": number,
      "material": "string",
      "part_count": number
    },

    "export_info": {
      "stl_file": "string",
      "3mf_file": "string",
      "export_date": "timestamp",
      "scale": "mm"
    },

    "print_recommendations": {
      "print_orientation": "string",
      "supports_required": boolean,
      "support_type": "string",
      "estimated_print_time_hours": number,
      "estimated_weight_g": number,
      "estimated_material_cost": "string"
    },

    "quality_metrics": {
      "wall_thickness_min_mm": number,
      "wall_thickness_max_mm": number,
      "overhang_angles": [number],
      "hollow_sections": number
    }
  }
}
```

## Error Handling

### Invalid Specifications
- Identify missing or contradictory specifications
- Suggest clarifications
- Offer reasonable defaults with reasoning
- Block generation if critical issues exist

### Model Generation Failures
- Log OpenSCAD errors
- Suggest parameter adjustments
- Provide simplified alternative
- Request user input on design decisions

### Printability Issues
- Flag problematic geometries
- Suggest modifications
- Offer alternative orientations
- Provide support material guidance

## Success Criteria

- [ ] All design specifications converted to OpenSCAD models
- [ ] Models are parametric and editable
- [ ] Printability validation passes
- [ ] STL exports are correct and valid
- [ ] Preview images generated successfully
- [ ] Metadata complete and accurate
- [ ] Multi-part assemblies handled correctly
- [ ] Model files properly organized and documented
