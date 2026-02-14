# 3D-ADK Design Phase Agent Specification

## Overview
Translates user requirements into visual design specifications and technical blueprints through an interview-based workflow.

## Core Phases

### 1. Interview Mode
Transform user intent into design requirements through structured conversation.

**Goals:**
- Understand object purpose and function
- Gather size and scale requirements
- Identify material preferences
- Understand aesthetic preferences
- Document constraints and limitations

**Key Questions to Ask:**
- What is the primary use of this object?
- What are the approximate dimensions?
- What materials should it be (PLA, PETG, resin, etc.)?
- Are there specific constraints (weight, strength, flexibility)?
- What aesthetic style (minimalist, ornate, realistic, etc.)?
- Does it have moving parts or assemblies?
- Are there existing designs to reference?

**Process:**
- Use Claude's conversational capabilities for natural dialogue
- Ask follow-up questions based on responses
- Refine understanding through clarification
- Store all responses in `interview.json`
- Generate intermediate summary for user confirmation

**Output:**
```json
{
  "design_brief": {
    "name": "string",
    "purpose": "string",
    "dimensions": {"width": "...", "height": "...", "depth": "..."},
    "materials": ["..."],
    "aesthetics": "string",
    "constraints": ["..."],
    "special_requirements": ["..."]
  }
}
```

### 2. Sketch Generation
Create initial conceptual sketches based on interview results.

**Process:**
- Generate multiple sketch variations (3-5 options)
- Show different angles and perspectives
- Include annotations for key features
- Use visual language consistent with design brief
- Save as PNG/image files

**Prompting Strategy:**
- Build detailed image prompt from design brief
- Emphasize form and proportion
- Include style guidance from interview
- Request specific views (front, side, 3/4)

**Output:**
- Multiple sketch images with descriptions
- Sketch metadata (dimensions, key features)

### 3. Image Generation
Produce high-quality rendered visualizations of approved designs.

**Process:**
- Request user feedback on sketches
- Generate detailed renders of selected sketch
- Create multiple perspective views
- Show material/color variations if requested
- Include dimension overlays if relevant

**Prompting Strategy:**
- Use approved sketch as reference
- Add material and lighting details
- Request production-quality renders
- Include realistic proportions and scale

**Output:**
- High-resolution render images
- Image metadata and generation parameters

### 4. Blueprint Creation
Generate formal technical specifications and assembly documentation.

**Content:**
- Dimensions with tolerances
- Material specifications
- Assembly instructions (if multi-part)
- Print orientation recommendations
- Support structure guidance
- Surface finish specifications
- Assembly part list with quantities

**Process:**
- Extract dimensions from design brief
- Calculate derived dimensions (wall thickness, infill parameters)
- Generate formal blueprint document
- Create assembly diagrams if needed
- Save as markdown + embedded images

**Output:**
```markdown
# Blueprint: [Project Name]

## Design Summary
[Brief description from interview]

## Specifications
- Overall Dimensions: [measurements]
- Material: [specification]
- Wall Thickness: [measurement]
- Infill: [percentage/type]

## Print Parameters
- Orientation: [orientation]
- Supports: [yes/no + type]
- Estimated Print Time: [duration]
- Estimated Weight: [weight]

## Assembly (if multi-part)
[Assembly instructions with diagrams]

## Notes
[Special requirements and considerations]
```

## Regeneration Loop

Users can request regenerations at any stage:
- **Regenerate Sketches**: New sketch variations with same brief
- **Regenerate Images**: New renders with different perspectives/materials
- **Regenerate Blueprint**: Updated specs based on feedback

**Process:**
- Maintain interview context throughout
- Apply user feedback to new generations
- Keep version history of all outputs
- Update design brief with clarifications

## Design Specifications JSON

Store all design information for handoff to modeling phase:

```json
{
  "project_id": "uuid",
  "project_name": "string",
  "created_at": "timestamp",
  "design_brief": {...},
  "specifications": {
    "overall_dimensions": {...},
    "material": "string",
    "wall_thickness_mm": number,
    "infill_percentage": number,
    "print_orientation": "string",
    "supports_required": boolean,
    "support_type": "string",
    "estimated_weight_g": number,
    "estimated_print_time_hours": number
  },
  "parts": [
    {
      "name": "string",
      "quantity": number,
      "dimensions": {...},
      "tolerance_mm": number
    }
  ],
  "assembly_instructions": [...]
}
```

## Error Handling

### Ambiguous Specifications
- Ask clarifying questions
- Present options for user choice
- Document final decision

### Infeasible Designs
- Alert user to printability concerns
- Suggest modifications
- Provide reasoning for concerns
- Offer redesign options

### Missing Information
- Identify gaps
- Ask targeted follow-up questions
- Offer reasonable defaults
- Document assumptions

## Success Criteria

- [ ] User interview captures all essential requirements
- [ ] Sketches accurately represent user intent
- [ ] Final images are production-quality and visually appropriate
- [ ] Blueprint contains all necessary technical information
- [ ] Design specifications are complete and unambiguous
- [ ] Regeneration loop works smoothly
- [ ] All outputs properly formatted and documented
