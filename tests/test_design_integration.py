"""Integration tests for complete design workflow (TICKET-008).

Tests the end-to-end design pipeline: interview → sketches → images → blueprint
Verifies data flows correctly between tools, files created, regenerations work,
and error handling is robust across tool boundaries.
"""

import asyncio
import json
import os
import pytest
import importlib
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import src.config
import src.tools.design_tools


# ============================================================================
# SHARED FIXTURES
# ============================================================================

@pytest.fixture
def tmp_projects_dir(tmp_path):
    """Create a temporary projects directory for testing."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return str(projects_dir)


@pytest.fixture
def mock_projects_dir(tmp_projects_dir, monkeypatch):
    """Patch PROJECTS_DIR to use temporary directory and reload design_tools."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("PROJECTS_DIR", tmp_projects_dir)
    monkeypatch.setattr(src.config, "PROJECTS_DIR", tmp_projects_dir)
    importlib.reload(src.tools.design_tools)
    return tmp_projects_dir


@pytest.fixture(autouse=True)
def reset_imports(mock_projects_dir):
    """Reset imports after each test to clear module state."""
    yield
    importlib.reload(src.tools.design_tools)


@pytest.fixture
def mock_anthropic(monkeypatch):
    """Mock Anthropic client for sketch and image generation."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Return a valid JSON array of 5 prompts
    mock_response.content = [MagicMock(text='["prompt1", "prompt2", "prompt3", "prompt4", "prompt5"]')]
    mock_client.messages.create = MagicMock(return_value=mock_response)
    monkeypatch.setattr("src.tools.design_tools._get_anthropic_client", lambda: mock_client)
    return mock_client


# Standard interview answers for test workflows
INTERVIEW_ANSWERS = [
    "phone stand",              # object_name
    "100mm x 80mm x 60mm",      # dimensions
    "PLA",                      # materials
    "minimalist modern",        # aesthetics
    "must fit iPhone 14",       # constraints
    "no",                       # moving_parts
    "none",                     # special_requirements
]


async def run_complete_interview(project_name: str) -> dict:
    """Helper: run all 7 interview questions and return final result."""
    from src.tools.design_tools import conduct_interview

    result = None
    for answer in INTERVIEW_ANSWERS:
        result = await conduct_interview(answer, project_name)
    return result


# ============================================================================
# TEST CLASS 1: Interview-to-Blueprint Pipeline
# ============================================================================

class TestInterviewToBlueprintPipeline:
    """Tests the linear happy path: interview → sketches → images → blueprint."""

    @pytest.mark.asyncio
    async def test_complete_interview_produces_design_brief(self, mock_projects_dir):
        """Running all 7 interview answers produces a complete design_brief."""
        from src.tools.design_tools import conduct_interview

        project_name = "test-project"
        result = await run_complete_interview(project_name)

        # Verify interview is complete
        assert result["status"] == "complete"
        assert result["interview_complete"] is True

        # Verify design_brief has all required keys
        design_brief = result["design_brief"]
        required_keys = {"name", "purpose", "dimensions", "materials", "aesthetics", "constraints", "special_requirements"}
        assert set(design_brief.keys()) == required_keys

        # Verify types
        assert isinstance(design_brief["dimensions"], dict)
        assert "width" in design_brief["dimensions"]
        assert "height" in design_brief["dimensions"]
        assert "depth" in design_brief["dimensions"]
        assert isinstance(design_brief["materials"], list)
        assert isinstance(design_brief["constraints"], list)
        assert isinstance(design_brief["special_requirements"], list)

    @pytest.mark.asyncio
    async def test_sketches_generated_from_interview_brief(self, mock_projects_dir, mock_anthropic):
        """After completing interview, sketches are generated from the design_brief."""
        from src.tools.design_tools import generate_sketches

        project_name = "test-project"
        interview_result = await run_complete_interview(project_name)
        design_brief = interview_result["design_brief"]

        # Generate sketches from the design brief
        sketch_result = await generate_sketches(project_name, design_brief)

        # Verify success
        assert sketch_result["status"] == "ok"
        assert sketch_result["sketch_count"] >= 3
        assert len(sketch_result["sketches"]) >= 3

        # Verify metadata file was created
        sketches_dir = Path(mock_projects_dir) / project_name / "design" / "sketches"
        assert sketches_dir.exists()
        metadata_path = sketches_dir / "metadata.json"
        assert metadata_path.exists()

    @pytest.mark.asyncio
    async def test_images_generated_for_each_perspective(self, mock_projects_dir, mock_anthropic):
        """Images are generated for all 4 perspectives and accumulate in metadata."""
        from src.tools.design_tools import generate_images

        project_name = "test-project"
        sketch_id = "test_sketch_123"
        perspectives = ["front", "side", "3d", "top"]

        # Generate images for each perspective
        image_results = []
        for perspective in perspectives:
            result = await generate_images(project_name, sketch_id, perspective)
            assert result["status"] == "ok"
            assert result["perspective"] == perspective
            image_results.append(result)

        # Verify metadata file has all 4 images
        images_dir = Path(mock_projects_dir) / project_name / "design" / "images"
        metadata_path = images_dir / "metadata.json"
        assert metadata_path.exists()

        with open(metadata_path) as f:
            metadata = json.load(f)

        assert len(metadata["images"]) == 4
        perspectives_found = [img["perspective"] for img in metadata["images"]]
        assert set(perspectives_found) == set(perspectives)

    @pytest.mark.asyncio
    async def test_blueprint_generated_from_complete_brief(self, mock_projects_dir):
        """Blueprint is generated from design brief with all required sections and specs."""
        from src.tools.design_tools import generate_blueprint

        project_name = "test-project"
        interview_result = await run_complete_interview(project_name)
        design_brief = interview_result["design_brief"]

        # Generate blueprint
        blueprint_result = await generate_blueprint(project_name, design_brief, ["image_001", "image_002"])

        # Verify success
        assert blueprint_result["status"] == "ok"
        assert "blueprint_path" in blueprint_result
        assert "specs_path" in blueprint_result

        # Verify files exist
        blueprint_path = Path(blueprint_result["blueprint_path"])
        specs_path = Path(blueprint_result["specs_path"])
        assert blueprint_path.exists()
        assert specs_path.exists()


# ============================================================================
# TEST CLASS 2: Full Pipeline Output Files
# ============================================================================

class TestFullPipelineOutputFiles:
    """Verifies all output files exist in correct locations after full pipeline."""

    @pytest.mark.asyncio
    async def test_all_output_files_created_in_correct_directories(self, mock_projects_dir, mock_anthropic):
        """All output files created in expected locations under design/ directory."""
        from src.tools.design_tools import generate_sketches, generate_images, generate_blueprint

        project_name = "test-project"

        # Run complete interview
        interview_result = await run_complete_interview(project_name)
        design_brief = interview_result["design_brief"]

        # Generate sketches
        sketch_result = await generate_sketches(project_name, design_brief)
        sketch_id = sketch_result["sketches"][0]["id"]

        # Generate images
        await generate_images(project_name, sketch_id, "front")

        # Generate blueprint
        await generate_blueprint(project_name, design_brief, [])

        # Verify all files exist
        design_dir = Path(mock_projects_dir) / project_name / "design"
        assert (design_dir / "interview.json").exists()
        assert (design_dir / "sketches" / "metadata.json").exists()
        assert (design_dir / "images" / "metadata.json").exists()
        assert (design_dir / "blueprint.md").exists()
        assert (design_dir / "design_specs.json").exists()

    @pytest.mark.asyncio
    async def test_design_specs_json_is_valid_for_modeling_agent(self, mock_projects_dir):
        """design_specs.json has all required keys for modeling agent."""
        from src.tools.design_tools import generate_blueprint

        project_name = "test-project"
        interview_result = await run_complete_interview(project_name)
        design_brief = interview_result["design_brief"]

        # Generate blueprint
        await generate_blueprint(project_name, design_brief, ["img_001"])

        # Verify specs.json structure
        specs_path = Path(mock_projects_dir) / project_name / "design" / "design_specs.json"
        with open(specs_path) as f:
            specs = json.load(f)

        # Top-level keys
        required_top_level = {
            "project_id", "project_name", "created_at", "design_brief",
            "specifications", "approved_images", "parts", "assembly_instructions"
        }
        assert set(specs.keys()) == required_top_level

        # Specifications nested keys (9 required)
        required_specs_keys = {
            "overall_dimensions", "material", "wall_thickness_mm",
            "infill_percentage", "print_orientation", "supports_required",
            "support_type", "estimated_weight_g", "estimated_print_time_hours"
        }
        assert set(specs["specifications"].keys()) == required_specs_keys

        # Verify approved_images passed through
        assert specs["approved_images"] == ["img_001"]

    @pytest.mark.asyncio
    async def test_blueprint_md_contains_all_required_sections(self, mock_projects_dir):
        """blueprint.md contains all required sections."""
        from src.tools.design_tools import generate_blueprint

        project_name = "test-project"
        interview_result = await run_complete_interview(project_name)
        design_brief = interview_result["design_brief"]

        # Generate blueprint
        await generate_blueprint(project_name, design_brief, [])

        # Verify sections
        blueprint_path = Path(mock_projects_dir) / project_name / "design" / "blueprint.md"
        with open(blueprint_path) as f:
            content = f.read()

        required_sections = [
            "# Blueprint:",
            "## Design Summary",
            "## Specifications",
            "## Print Parameters",
            "Overall Dimensions:",
            "Material:",
            "Wall Thickness:",
            "Infill:",
            "Orientation:",
            "Estimated Print Time:",
            "Estimated Weight:",
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"


# ============================================================================
# TEST CLASS 3: Regeneration Workflows
# ============================================================================

class TestRegenerationWorkflows:
    """Tests that regeneration updates state correctly."""

    @pytest.mark.asyncio
    async def test_sketch_regeneration_adds_new_sketches(self, mock_projects_dir, mock_anthropic):
        """Calling generate_sketches twice accumulates sketches in metadata."""
        from src.tools.design_tools import generate_sketches

        project_name = "test-project"
        interview_result = await run_complete_interview(project_name)
        design_brief = interview_result["design_brief"]

        # First sketch generation
        result1 = await generate_sketches(project_name, design_brief)
        # Each call generates 5 sketches, but we verify accumulation in metadata

        # Second sketch generation (regeneration)
        result2 = await generate_sketches(project_name, design_brief)

        # Verify metadata accumulated total sketches
        metadata_path = Path(mock_projects_dir) / project_name / "design" / "sketches" / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Should have sketches from both calls (5 + 5 = 10)
        total_sketches = len(metadata["sketches"])
        assert total_sketches >= 10, f"Expected at least 10 accumulated sketches, got {total_sketches}"

    @pytest.mark.asyncio
    async def test_image_regeneration_with_feedback_creates_new_record(self, mock_projects_dir, mock_anthropic):
        """Image regeneration with feedback parameter creates new image record."""
        from src.tools.design_tools import generate_images

        project_name = "test-project"
        sketch_id = "sketch_abc"

        # First image generation
        result1 = await generate_images(project_name, sketch_id, "front")
        assert result1["status"] == "ok"

        # Regeneration with feedback
        result2 = await generate_images(
            project_name, sketch_id, "front",
            feedback="make it rounder and more ergonomic"
        )
        assert result2["status"] == "ok"
        assert len(result2["images"]) >= 1

        # Verify feedback influenced the prompt (if present in result)
        # The feedback should be incorporated into the image prompt
        if "feedback" in result2["images"][0]:
            assert "rounder" in result2["images"][0]["feedback"].lower() or \
                   "ergonomic" in result2["images"][0]["feedback"].lower()

    @pytest.mark.asyncio
    async def test_image_all_four_perspectives_accumulate_in_metadata(self, mock_projects_dir, mock_anthropic):
        """Calling generate_images for all perspectives accumulates them."""
        from src.tools.design_tools import generate_images

        project_name = "test-project"
        sketch_id = "sketch_xyz"
        perspectives = ["front", "side", "3d", "top"]

        # Generate images for each perspective
        for perspective in perspectives:
            await generate_images(project_name, sketch_id, perspective)

        # Verify all accumulated in metadata
        metadata_path = Path(mock_projects_dir) / project_name / "design" / "images" / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        assert len(metadata["images"]) == 4
        perspectives_found = [img["perspective"] for img in metadata["images"]]
        assert set(perspectives_found) == set(perspectives)

    @pytest.mark.asyncio
    async def test_blueprint_regeneration_overwrites_files(self, mock_projects_dir):
        """Calling generate_blueprint twice overwrites the files with latest data."""
        from src.tools.design_tools import generate_blueprint

        project_name = "test-project"

        # First design
        brief1 = {
            "name": "phone stand v1",
            "purpose": "desk organization",
            "dimensions": {"width": 100, "height": 80, "depth": 60},
            "materials": ["PLA"],
            "aesthetics": "minimalist",
            "constraints": [],
            "special_requirements": []
        }

        # First blueprint generation
        await generate_blueprint(project_name, brief1, [])
        blueprint_path = Path(mock_projects_dir) / project_name / "design" / "blueprint.md"
        with open(blueprint_path) as f:
            content1 = f.read()
        assert "desk" in content1 or "PLA" in content1

        # Second design (different materials and purpose)
        brief2 = {
            "name": "phone stand v2",
            "purpose": "bedside table",
            "dimensions": {"width": 120, "height": 100, "depth": 70},
            "materials": ["PETG"],
            "aesthetics": "elegant",
            "constraints": ["strong"],
            "special_requirements": []
        }

        # Second blueprint generation (regeneration)
        await generate_blueprint(project_name, brief2, [])
        with open(blueprint_path) as f:
            content2 = f.read()

        # Verify overwrite - new material should be present, old should not
        assert "PETG" in content2, "New material PETG should be in regenerated blueprint"
        assert "PLA" not in content2, "Old material PLA should not be in regenerated blueprint"
        assert "bedside" in content2.lower(), "New purpose should be reflected in regenerated blueprint"


# ============================================================================
# TEST CLASS 4: Error Handling Integration
# ============================================================================

class TestErrorHandlingIntegration:
    """Tests error handling in cross-tool scenarios."""

    @pytest.mark.asyncio
    async def test_generate_images_without_prior_interview_still_works(self, mock_projects_dir, mock_anthropic):
        """Image generation works even without prior interview.json (graceful degradation)."""
        from src.tools.design_tools import generate_images

        project_name = "test-project"
        sketch_id = "sketch_123"

        # Call generate_images without running interview first
        result = await generate_images(project_name, sketch_id, "front")

        # Should still succeed (graceful fallback)
        assert result["status"] == "ok"
        assert len(result["images"]) >= 1

        # Verify image record created
        images_dir = Path(mock_projects_dir) / project_name / "design" / "images"
        assert images_dir.exists()

    @pytest.mark.asyncio
    async def test_blueprint_with_minimal_design_brief(self, mock_projects_dir):
        """Blueprint generation works with minimal design brief (only name + purpose)."""
        from src.tools.design_tools import generate_blueprint

        project_name = "test-project"
        minimal_brief = {
            "name": "minimal design",
            "purpose": "testing",
            "dimensions": {},
            "materials": [],
            "aesthetics": "",
            "constraints": [],
            "special_requirements": []
        }

        # Generate blueprint with minimal data
        result = await generate_blueprint(project_name, minimal_brief, [])

        # Should succeed with defaults
        assert result["status"] == "ok"

        # Verify defaults are applied
        specs_path = Path(mock_projects_dir) / project_name / "design" / "design_specs.json"
        with open(specs_path) as f:
            specs = json.load(f)

        # Default material should be PLA
        assert specs["specifications"]["material"] == "PLA"
        # Should have default infill
        assert "infill_percentage" in specs["specifications"]
        assert specs["specifications"]["infill_percentage"] > 0

    @pytest.mark.asyncio
    async def test_pipeline_with_special_project_name_characters(self, mock_projects_dir, mock_anthropic):
        """Pipeline works with special characters in project name (spaces, dashes, etc)."""
        from src.tools.design_tools import generate_sketches

        # Project names with special characters but valid for filesystems
        project_names = [
            "my-project-123",
            "project_with_underscore",
            "project.with.dots",
        ]

        interview_result = await run_complete_interview(project_names[0])
        design_brief = interview_result["design_brief"]

        for project_name in project_names:
            result = await generate_sketches(project_name, design_brief)
            assert result["status"] == "ok", f"Failed for project: {project_name}"

            # Verify directory created
            sketches_dir = Path(mock_projects_dir) / project_name / "design" / "sketches"
            assert sketches_dir.exists(), f"Directory not created for: {project_name}"

    @pytest.mark.asyncio
    async def test_error_recovery_and_state_isolation(self, mock_projects_dir, mock_anthropic):
        """Error in one tool call doesn't affect subsequent tool calls."""
        from src.tools.design_tools import generate_sketches

        design_brief = {
            "name": "test",
            "purpose": "test",
            "dimensions": {},
            "materials": [],
            "aesthetics": "test",
            "constraints": [],
            "special_requirements": []
        }

        # Call with empty project name (should fail)
        result_error = await generate_sketches("", design_brief)
        assert result_error["status"] == "error"

        # Next call with valid project name should succeed (no state pollution)
        result_success = await generate_sketches("valid-project", design_brief)
        assert result_success["status"] == "ok"

        # Verify successful call created files
        sketches_dir = Path(mock_projects_dir) / "valid-project" / "design" / "sketches"
        assert sketches_dir.exists()
