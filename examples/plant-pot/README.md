# Example: Small Plant Pot

A decorative plant pot for small succulents or herbs, designed with drainage holes and modern aesthetics.

## Design Brief

This example shows a simple geometric design suitable for beginners.

**Objective:** Create a plant pot that:
- Holds small succulents or herbs (4cm diameter soil area)
- Has drainage holes for plant health
- Modern, minimalist design
- Suitable for window sill or desk
- Can be customized in different colors

**Materials:** PLA (safe for plants with proper finishing)
**Print Time:** ~1.5 hours
**Weight:** ~30g

## Input: Design Brief (design_brief.json)

Simple user requirements:

```json
{
  "object_name": "Small Succulent Pot",
  "purpose": "Plant container for succulents",
  "dimensions": {
    "width_mm": 70,
    "depth_mm": 70,
    "height_mm": 60
  },
  "materials": ["PLA"],
  "aesthetics": "Modern, minimalist",
  "constraints": [
    "Drainage holes required",
    "Lightweight",
    "Simple geometry for reliability"
  ],
  "special_requirements": [
    "Drainage holes (3-4 at bottom)",
    "Smooth interior for root growth"
  ]
}
```

## Output: Design Specifications (design_specs.json)

Simplified specification for this straightforward design:

```json
{
  "project_name": "small_succulent_pot",
  "design_intent": "Simple minimalist plant pot with drainage holes",
  "dimensions": {
    "overall_width_mm": 70,
    "overall_depth_mm": 70,
    "overall_height_mm": 65,
    "pot_thickness_mm": 2,
    "drainage_hole_count": 4,
    "drainage_hole_diameter_mm": 3
  },
  "material": "PLA",
  "print_settings": {
    "wall_thickness_mm": 2.0,
    "infill_percentage": 8,
    "supports_required": false,
    "estimated_print_time_hours": 1.5,
    "estimated_weight_grams": 30,
    "estimated_filament_length_mm": 3600
  },
  "assembly": "single_part",
  "post_processing": [
    "Smooth interior surfaces",
    "Optional: Food-safe sealant if desired"
  ],
  "simplicity": "Very High - Perfect for beginner prints"
}
```

## Why This Example?

This example is ideal for:
- **First-time printers** - No supports, simple geometry
- **Quick prints** - Ready in ~90 minutes
- **Low risk** - Minimal failure points
- **Practical** - Actually useful finished product

## Printing

**Settings:**
- **Infill:** 8% (lightweight)
- **Nozzle:** 200°C
- **Bed:** 60°C
- **No supports needed**
- **Print time:** ~1.5 hours

## Quality Expectations

Expected success:
- ✓ No supports needed
- ✓ Easy removal from bed
- ✓ Smooth surfaces
- ✓ Accurate drainage holes
- ✓ Ready to use (after cleanup)

## Post-Processing

1. Remove from bed
2. Clean up any z-seam
3. Smooth interior if desired (optional)
4. Dry completely before planting
5. Add plant and soil

## Assembly

No assembly required - single-part design!

---

**Time to print:** ~1.5 hours
**Material cost:** ~$0.15
**Success rate:** Very High (simple design)
**Best for:** Beginner prints, quick projects
