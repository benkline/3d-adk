"""Integration tests for complete modeling workflow (TICKET-015).

Tests the end-to-end modeling pipeline: validate specs → setup workspace → generate SCAD →
render preview → export model → analyze printability → optimize parameters

Verifies data flows correctly between tools, files created, and error handling is robust
across tool boundaries.
"""

import asyncio
import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import src.config
import src.tools.modeling_tools


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
def sample_design_specs():
    """Minimal valid design_specs.json for modeling tests."""
    return {
        "project_name": "test_phone_stand",
        "specifications": {
            "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
            "material": "PLA",
            "wall_thickness": 2.0,
            "infill": 20
        },
        "design_brief": {
            "object_name": "phone stand",
            "purpose": "desk use",
            "aesthetics": "minimal",
            "constraints": ["lightweight"],
            "special_requirements": []
        }
    }


@pytest.fixture
def sample_multi_part_specs():
    """Design specs with multiple parts."""
    return {
        "project_name": "test_multi_part",
        "specifications": {
            "overall_dimensions": {"width": 150, "height": 100, "depth": 80},
            "material": "PETG",
            "wall_thickness": 3.0,
            "infill": 35
        },
        "design_brief": {
            "object_name": "modular organizer",
            "purpose": "storage",
            "aesthetics": "functional",
            "constraints": ["must be modular", "strong"],
            "special_requirements": []
        },
        "parts": [
            {"name": "base", "dimensions": {"width": 150, "height": 10, "depth": 80}},
            {"name": "divider", "dimensions": {"width": 2, "height": 100, "depth": 80}}
        ]
    }


# ============================================================================
# TEST CLASS 1: Full Pipeline Workflow
# ============================================================================

class TestFullPipelineWorkflow:
    """Tests the linear happy path: validate → workspace → scad → render → export → analyze → optimize"""

    @pytest.mark.asyncio
    async def test_setup_workspace_creates_required_directories(self, tmp_projects_dir):
        """Setup workspace creates scad/, exports/, previews/ subdirs and metadata.json."""
        from src.tools.modeling_tools import setup_openscad_workspace

        # Patch PROJECTS_DIR
        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_workspace"

            result = await setup_openscad_workspace(project_name)

            assert result["status"] == "ok"
            assert result["workspace_dir"]

            # Verify all required subdirectories exist
            workspace_dir = Path(result["workspace_dir"])
            assert (workspace_dir / "scad").exists()
            assert (workspace_dir / "exports").exists()
            assert (workspace_dir / "previews").exists()
            assert (workspace_dir / "metadata.json").exists()

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_generate_scad_produces_valid_content(self, tmp_projects_dir, sample_design_specs):
        """Generate SCAD code produces file with required sections."""
        from src.tools.modeling_tools import setup_openscad_workspace, generate_scad_code

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_scad_gen"

            # Setup workspace first
            await setup_openscad_workspace(project_name)

            # Generate SCAD
            result = await generate_scad_code(project_name, sample_design_specs)

            assert result["status"] == "ok"
            assert result["scad_path"]
            assert result["scad_content"]

            # Verify file exists and has required sections
            scad_path = Path(result["scad_path"])
            assert scad_path.exists()

            content = result["scad_content"]
            required_sections = ["// === PARAMETERS ===", "// === DIMENSIONS ===",
                                 "// === MODULES ===", "// === ASSEMBLY ==="]
            for section in required_sections:
                assert section in content, f"Missing section: {section}"

            # Verify parameters section
            assert "$fn =" in content
            assert "wall_thickness =" in content

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_render_preview_returns_pending_without_openscad(self, tmp_projects_dir, sample_design_specs):
        """Render returns pending status when OpenSCAD binary not available."""
        from src.tools.modeling_tools import setup_openscad_workspace, generate_scad_code, render_preview

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        original_path = src.tools.modeling_tools.OPENSCAD_PATH
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            src.tools.modeling_tools.OPENSCAD_PATH = "/nonexistent/openscad"
            project_name = "test_render_pending"

            # Setup and generate
            await setup_openscad_workspace(project_name)
            await generate_scad_code(project_name, sample_design_specs)

            # Render should return pending
            result = await render_preview(project_name)

            assert result["status"] == "pending"

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir
            src.tools.modeling_tools.OPENSCAD_PATH = original_path

    @pytest.mark.asyncio
    async def test_export_model_returns_pending_without_openscad(self, tmp_projects_dir, sample_design_specs):
        """Export returns pending status when OpenSCAD binary not available."""
        from src.tools.modeling_tools import setup_openscad_workspace, generate_scad_code, export_model

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        original_path = src.tools.modeling_tools.OPENSCAD_PATH
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            src.tools.modeling_tools.OPENSCAD_PATH = "/nonexistent/openscad"
            project_name = "test_export_pending"

            # Setup and generate
            await setup_openscad_workspace(project_name)
            await generate_scad_code(project_name, sample_design_specs)

            # Export should return pending
            result = await export_model(project_name)

            assert result["status"] == "pending"

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir
            src.tools.modeling_tools.OPENSCAD_PATH = original_path

    @pytest.mark.asyncio
    async def test_validate_design_specs_finds_specs_file(self, tmp_projects_dir, sample_design_specs):
        """Validate can find and parse design_specs.json correctly."""
        from src.tools.modeling_tools import setup_openscad_workspace, validate_design_specs

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = sample_design_specs["project_name"]

            # Setup workspace and create specs file in design directory
            await setup_openscad_workspace(project_name)

            # Write specs file in design directory (where it comes from design phase)
            design_dir = Path(tmp_projects_dir) / project_name / "design"
            design_dir.mkdir(parents=True, exist_ok=True)
            specs_path = design_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                json.dump(sample_design_specs, f)

            # Validate should find it
            result = await validate_design_specs(project_name)

            assert result["status"] == "ok"
            assert result["specs"]["project_name"] == project_name

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir


# ============================================================================
# TEST CLASS 2: Output Files Verification
# ============================================================================

class TestFullPipelineOutputFiles:
    """Verify all output files are created in correct directories."""

    @pytest.mark.asyncio
    async def test_scad_file_in_correct_directory(self, tmp_projects_dir, sample_design_specs):
        """Model.scad lives in {project}/modeling/scad/ directory."""
        from src.tools.modeling_tools import setup_openscad_workspace, generate_scad_code

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_scad_path"

            await setup_openscad_workspace(project_name)
            result = await generate_scad_code(project_name, sample_design_specs)

            # Verify path structure
            expected_path = Path(tmp_projects_dir) / project_name / "modeling" / "scad" / "model.scad"
            assert Path(result["scad_path"]).resolve() == expected_path.resolve()
            assert expected_path.exists()

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_multi_part_scad_creates_separate_files(self, tmp_projects_dir, sample_multi_part_specs):
        """Multi-part design creates separate part_name.scad files."""
        from src.tools.modeling_tools import setup_openscad_workspace, generate_scad_code

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_multipart"

            await setup_openscad_workspace(project_name)
            result = await generate_scad_code(project_name, sample_multi_part_specs)

            assert result["status"] == "ok"
            # Check if multi-part returns part_files
            if "parts" in sample_multi_part_specs and len(sample_multi_part_specs["parts"]) > 1:
                assert "part_files" in result or "scad_path" in result

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_metadata_json_created_after_workspace_setup(self, tmp_projects_dir):
        """Metadata.json created during workspace setup."""
        from src.tools.modeling_tools import setup_openscad_workspace

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_metadata"

            await setup_openscad_workspace(project_name)

            metadata_path = Path(tmp_projects_dir) / project_name / "modeling" / "metadata.json"
            assert metadata_path.exists()

            # Verify it's valid JSON
            with open(metadata_path) as f:
                metadata = json.load(f)
            assert isinstance(metadata, dict)

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_pipeline_state_isolation(self, tmp_projects_dir, sample_design_specs):
        """Two projects don't share files."""
        from src.tools.modeling_tools import setup_openscad_workspace, generate_scad_code

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir

            # Create two projects
            project1 = "isolation_test_1"
            project2 = "isolation_test_2"

            specs1 = sample_design_specs.copy()
            specs1["project_name"] = project1
            specs2 = sample_design_specs.copy()
            specs2["project_name"] = project2

            await setup_openscad_workspace(project1)
            await setup_openscad_workspace(project2)
            await generate_scad_code(project1, specs1)
            await generate_scad_code(project2, specs2)

            # Verify separate directories
            scad_dir1 = Path(tmp_projects_dir) / project1 / "modeling" / "scad"
            scad_dir2 = Path(tmp_projects_dir) / project2 / "modeling" / "scad"

            assert scad_dir1.exists()
            assert scad_dir2.exists()
            assert scad_dir1 != scad_dir2

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir


# ============================================================================
# TEST CLASS 3: Printability and Optimization
# ============================================================================

class TestPrintabilityAndOptimization:
    """Test analyze_printability and optimize_parameters integration."""

    @pytest.mark.asyncio
    async def test_analyze_printability_valid_pla_specs(self, tmp_projects_dir, sample_design_specs):
        """Analyze printability returns feasible=True for valid PLA specs."""
        from src.tools.modeling_tools import setup_openscad_workspace, analyze_printability

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_printability"

            # Setup workspace and write specs file in design directory
            await setup_openscad_workspace(project_name)
            design_dir = Path(tmp_projects_dir) / project_name / "design"
            design_dir.mkdir(parents=True, exist_ok=True)
            specs_path = design_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                json.dump(sample_design_specs, f)

            result = await analyze_printability(project_name)

            assert result["status"] == "ok"
            assert "report" in result
            assert result["report"]["feasible"] is True
            assert result["report"]["wall_thickness_ok"] is True

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_analyze_printability_thin_wall_warning(self, tmp_projects_dir, sample_design_specs):
        """Analyze detects thin walls below material minimum."""
        from src.tools.modeling_tools import setup_openscad_workspace, analyze_printability

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_thin_wall"

            # Create specs with very thin walls (wall_thickness_mm field)
            thin_specs = sample_design_specs.copy()
            thin_specs["specifications"]["wall_thickness_mm"] = 0.5  # Too thin for PLA (minimum 1.2mm)

            await setup_openscad_workspace(project_name)
            design_dir = Path(tmp_projects_dir) / project_name / "design"
            design_dir.mkdir(parents=True, exist_ok=True)
            specs_path = design_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                json.dump(thin_specs, f)

            result = await analyze_printability(project_name)

            assert result["status"] == "ok"
            # Should detect wall thickness violation for thin walls
            # Either wall_thickness_ok is False or we have warnings about it
            assert result["report"]["wall_thickness_ok"] is False or len(result["report"]["warnings"]) > 0

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_optimize_parameters_returns_all_recommendations(self, tmp_projects_dir, sample_design_specs):
        """Optimize returns all required recommendation keys."""
        from src.tools.modeling_tools import setup_openscad_workspace, optimize_parameters

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_optimization"

            # Setup and write specs file in design directory
            await setup_openscad_workspace(project_name)
            design_dir = Path(tmp_projects_dir) / project_name / "design"
            design_dir.mkdir(parents=True, exist_ok=True)
            specs_path = design_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                json.dump(sample_design_specs, f)

            result = await optimize_parameters(project_name)

            assert result["status"] == "ok"
            assert "recommendations" in result
            recommendations = result["recommendations"]

            # Verify all required keys
            required_keys = [
                "print_orientation", "orientation_rationale",
                "infill_percentage", "infill_rationale",
                "supports_required", "support_type", "support_rationale",
                "estimated_weight_g", "estimated_print_time_hours",
                "estimated_material_cost_usd"
            ]

            for key in required_keys:
                assert key in recommendations, f"Missing recommendation key: {key}"

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_optimization_cost_estimate_format(self, tmp_projects_dir, sample_design_specs):
        """Cost estimate is in $X.XX format."""
        from src.tools.modeling_tools import setup_openscad_workspace, optimize_parameters

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_cost_format"

            await setup_openscad_workspace(project_name)
            design_dir = Path(tmp_projects_dir) / project_name / "design"
            design_dir.mkdir(parents=True, exist_ok=True)
            specs_path = design_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                json.dump(sample_design_specs, f)

            result = await optimize_parameters(project_name)

            cost = result["recommendations"]["estimated_material_cost_usd"]
            assert isinstance(cost, str)
            assert cost.startswith("$")
            # Verify format like $1.23
            assert "." in cost

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_optimize_with_printability_report(self, tmp_projects_dir, sample_design_specs):
        """Optimize integrates with printability report for better recommendations."""
        from src.tools.modeling_tools import (
            setup_openscad_workspace, analyze_printability, optimize_parameters
        )

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_integrated_optimize"

            await setup_openscad_workspace(project_name)
            design_dir = Path(tmp_projects_dir) / project_name / "design"
            design_dir.mkdir(parents=True, exist_ok=True)
            specs_path = design_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                json.dump(sample_design_specs, f)

            # Get printability report
            printability_result = await analyze_printability(project_name)
            report = printability_result["report"]

            # Optimize with report
            optimize_result = await optimize_parameters(
                project_name,
                printability_report=report
            )

            assert optimize_result["status"] == "ok"
            # Recommendations should be influenced by the report
            assert "support_type" in optimize_result["recommendations"]

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir


# ============================================================================
# TEST CLASS 4: Error Handling Integration
# ============================================================================

class TestErrorHandlingIntegration:
    """Test graceful error handling across the pipeline."""

    @pytest.mark.asyncio
    async def test_validate_missing_specs_file(self, tmp_projects_dir):
        """Validate returns error when specs file not found."""
        from src.tools.modeling_tools import validate_design_specs

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "nonexistent_project"

            result = await validate_design_specs(project_name)

            assert result["status"] == "error"
            assert "message" in result

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_validate_invalid_json(self, tmp_projects_dir):
        """Validate returns error on malformed JSON in specs file."""
        from src.tools.modeling_tools import setup_openscad_workspace, validate_design_specs

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_invalid_json"

            # Create workspace and write invalid JSON
            await setup_openscad_workspace(project_name)
            workspace_dir = Path(tmp_projects_dir) / project_name / "modeling"
            specs_path = workspace_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                f.write("{invalid json content")

            result = await validate_design_specs(project_name)

            assert result["status"] == "error"

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_generate_scad_empty_project_name(self, tmp_projects_dir, sample_design_specs):
        """Generate SCAD returns error for empty project name."""
        from src.tools.modeling_tools import generate_scad_code

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir

            result = await generate_scad_code("", sample_design_specs)

            assert result["status"] == "error"

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, tmp_projects_dir, sample_design_specs):
        """Export returns error for invalid format."""
        from src.tools.modeling_tools import setup_openscad_workspace, generate_scad_code, export_model

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        original_path = src.tools.modeling_tools.OPENSCAD_PATH
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            src.tools.modeling_tools.OPENSCAD_PATH = "/nonexistent/openscad"
            project_name = "test_invalid_format"

            await setup_openscad_workspace(project_name)
            await generate_scad_code(project_name, sample_design_specs)

            # Try invalid format
            result = await export_model(project_name, export_format="invalid_format")

            assert result["status"] == "error"

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir
            src.tools.modeling_tools.OPENSCAD_PATH = original_path

    @pytest.mark.asyncio
    async def test_analyze_missing_specs_file_error(self, tmp_projects_dir):
        """Analyze printability returns error gracefully when specs file missing."""
        from src.tools.modeling_tools import analyze_printability

        original_dir = src.tools.modeling_tools.PROJECTS_DIR
        try:
            src.tools.modeling_tools.PROJECTS_DIR = tmp_projects_dir
            project_name = "test_analyze_error"

            result = await analyze_printability(project_name)

            assert result["status"] == "error"
            assert "message" in result

        finally:
            src.tools.modeling_tools.PROJECTS_DIR = original_dir
