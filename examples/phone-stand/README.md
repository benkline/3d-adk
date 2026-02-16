# Example: Phone Stand

A minimalist phone stand designed to hold modern smartphones at an optimal viewing angle.

## Design Brief

This example shows a complete 3D-ADK workflow for designing and manufacturing a phone stand.

**Objective:** Create a desktop phone stand that:
- Securely holds iPhone 14 (or similar size smartphones)
- Provides optimal viewing angle (45°) for desk viewing
- Uses minimal material (eco-friendly)
- Has a non-slip base to prevent sliding
- Fits on any standard desk

**Materials:** PLA plastic
**Print Time:** ~2.5 hours
**Weight:** ~45g

## Input: Design Brief (interview.json)

The interview response capturing user requirements:

```json
{
  "object_name": "iPhone 14 Phone Stand",
  "purpose": "Desktop device holder for viewing",
  "dimensions": {
    "width_mm": 80,
    "depth_mm": 100,
    "height_mm": 120
  },
  "materials": ["PLA"],
  "aesthetics": "Minimalist, modern",
  "constraints": [
    "Must hold iPhone 14 securely",
    "Non-slip base required",
    "Lightweight",
    "Compact footprint"
  ],
  "special_requirements": [
    "Viewing angle: 45°",
    "Cable management: Small notch for charging cable"
  ]
}
```

## Output: Design Specifications (design_specs.json)

After the Design Agent processes the brief:

```json
{
  "project_name": "iphone_14_stand",
  "design_intent": "Minimalist desktop phone stand with optimal viewing angle",
  "dimensions": {
    "overall_width_mm": 85,
    "overall_depth_mm": 105,
    "overall_height_mm": 125,
    "base_thickness_mm": 8,
    "arm_thickness_mm": 3,
    "phone_slot_width_mm": 85,
    "phone_slot_depth_mm": 8
  },
  "material": "PLA",
  "material_properties": {
    "density": 1.24,
    "yield_strength_mpa": 60,
    "melting_point_c": 210
  },
  "geometry": {
    "base_shape": "rectangular",
    "base_features": "rounded_corners, non_slip_texture",
    "arm_shape": "curved_bracket",
    "phone_grip": "gentle_curves_with_friction_pads",
    "cable_management": "bottom_cable_slot"
  },
  "print_settings": {
    "wall_thickness_mm": 2.0,
    "infill_percentage": 10,
    "supports_required": false,
    "recommended_orientation": "upright",
    "estimated_print_time_hours": 2.5,
    "estimated_weight_grams": 45,
    "estimated_filament_length_mm": 5400
  },
  "assembly": "single_part",
  "post_processing": [
    "Sand base for non-slip finish",
    "Optional: Apply matte sealant"
  ]
}
```

## Generated Design Outputs

After running through the Design phase, the following files are created:

### 1. Interview Snapshot (interview.json)
- Raw user responses
- Exact requirements captured
- Allows for design regeneration if needed

### 2. Sketches (5 variations)
- Quick concept sketches showing different stand approaches
- Front, side, and isometric views
- Different arm angles and base designs

### 3. Rendered Images (4+ perspectives)
- Professional renders showing final design
- Front view: Shows phone mounting and viewing angle
- Side view: Demonstrates the 45° angle
- Isometric view: Overall form and proportions
- Top view: Base footprint and stability

### 4. Technical Blueprint (blueprint.md)
- Detailed technical specifications
- Dimension callouts
- Material specifications
- Assembly instructions (if multi-part)
- Tolerance information

### 5. Design Specs JSON (design_specs.json)
- Machine-readable specification
- Used as input to Modeling phase
- Contains all dimensions, materials, and print settings

## Modeling Phase Output

Once approved, the Modeling Agent generates:

- **project.scad** - Parametric OpenSCAD source code
- **model.stl** - Ready-to-print STL file (100-150 KB)
- **model.3mf** - Alternative format with metadata
- **preview_front.png** - Rendered preview from front
- **preview_isometric.png** - Rendered preview from isometric angle
- **printability_analysis.json** - Feasibility assessment (wall thickness OK, no overhangs, good stability)
- **optimization_recommendations.json** - Slice settings (10% infill, no supports needed, print time 2.5h)

## Printing

With the STL file, you can:

1. **Slice the model** in your preferred slicer (Cura, PrusaSlicer, etc.)
   - Infill: 10%
   - Nozzle: 200°C
   - Bed: 60°C
   - No supports needed
   - Print time: ~2.5 hours

2. **Print on any FDM printer** (Prusa i3, Ender 3, etc.)

3. **Post-process** (optional)
   - Sand the base for texture
   - Add rubber feet for grip

## Quality Results

Expected print quality:
- ✓ Smooth surfaces
- ✓ Accurate dimensions
- ✓ No supports needed
- ✓ Minimal cleanup

## How to Use This Example

1. Copy this directory to understand the workflow
2. Review the JSON files to see expected data structures
3. Use in your own 3D-ADK installation with `python src/main.py`
4. Run through the workflow to generate actual files

```bash
cd ~/Projects/3d-adk
python src/main.py

# In the CLI:
3d-adk> new "phone_stand"
# ... Design Agent interviews and generates sketches...
# ... Approve the design ...
# ... Modeling Agent generates OpenSCAD and STL ...
# ... Export and print!
```

---

**Time to print:** ~2.5 hours
**Material cost:** ~$0.30 (at $25/kg PLA)
**Success rate:** High (simple geometry, no supports)
