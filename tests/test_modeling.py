"""Tests for the modeling phase agent and tools."""

import os
import pytest
import json
import tempfile
import shutil
from pathlib import Path


class TestModelingAgent:
    """Tests for the modeling agent structure."""

    def test_modeling_agent_initializes(self):
        """Test that modeling agent initializes without errors."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        from src.agents.modeling import modeling_agent
        assert modeling_agent is not None

    def test_modeling_agent_has_correct_name(self):
        """Test that modeling agent has the correct name."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        from src.agents.modeling import modeling_agent
        assert modeling_agent.name == "modeling_phase_agent"

    def test_modeling_agent_has_five_tools(self):
        """Test that modeling agent has five tools."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        from src.agents.modeling import modeling_agent
        assert len(modeling_agent.tools) == 5

    def test_modeling_agent_uses_config_model(self):
        """Test that modeling agent uses configured LLM model."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        from src.agents.modeling import modeling_agent
        from src.config import LLM_MODEL
        assert modeling_agent.model == LLM_MODEL


class TestValidateDesignSpecs:
    """Tests for validate_design_specs tool."""

    @pytest.mark.asyncio
    async def test_validate_design_specs_with_valid_input(self):
        """Test validate_design_specs returns formatted response with valid input."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        # Create temporary test project with valid design specs
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create design specs
            project_dir = Path(tmpdir) / "test_project" / "design"
            project_dir.mkdir(parents=True, exist_ok=True)

            specs = {
                "project_name": "test_project",
                "specifications": {
                    "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                    "material": "PLA"
                },
                "design_brief": {"name": "test"}
            }

            specs_path = project_dir / "design_specs.json"
            with open(specs_path, "w") as f:
                json.dump(specs, f)

            from src.tools.modeling_tools import validate_design_specs
            result = await validate_design_specs("test_project", specs_path=str(specs_path))

            assert isinstance(result, dict)
            assert "status" in result
            assert result["status"] == "ok"
            assert "specs" in result
            assert "message" in result

    @pytest.mark.asyncio
    async def test_validate_design_specs_with_empty_project_name(self):
        """Test validate_design_specs returns error with empty project_name."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        from src.tools.modeling_tools import validate_design_specs
        result = await validate_design_specs("")

        assert result["status"] == "error"
        assert "message" in result


class TestSetupOpenSCADWorkspace:
    """Tests for setup_openscad_workspace tool."""

    @pytest.mark.asyncio
    async def test_setup_openscad_workspace_with_valid_input(self):
        """Test setup_openscad_workspace creates directory structure."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkeypatch the PROJECTS_DIR in the module
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                from src.tools.modeling_tools import setup_openscad_workspace
                result = await setup_openscad_workspace("test_project")

                assert isinstance(result, dict)
                assert "status" in result
                assert result["status"] == "ok"
                assert "workspace_dir" in result
                assert "message" in result

                # Verify directory structure was created
                workspace = Path(tmpdir) / "test_project" / "modeling"
                assert workspace.exists()
                assert (workspace / "scad").exists()
                assert (workspace / "exports").exists()
                assert (workspace / "previews").exists()
                assert (workspace / "metadata.json").exists()
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_setup_openscad_workspace_with_empty_project_name(self):
        """Test setup_openscad_workspace returns error with empty project_name."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        from src.tools.modeling_tools import setup_openscad_workspace
        result = await setup_openscad_workspace("")

        assert result["status"] == "error"
        assert "message" in result


class TestGenerateSCADCode:
    """Tests for generate_scad_code tool."""

    @pytest.mark.asyncio
    async def test_generate_scad_code_with_valid_input(self):
        """Test generate_scad_code returns formatted response with valid input."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkeypatch the PROJECTS_DIR in the module
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                # Create modeling directory
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA",
                        "wall_thickness_mm": 2
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert isinstance(result, dict)
                assert "status" in result
                assert result["status"] == "ok"
                assert "scad_path" in result
                assert "scad_content" in result
                assert "message" in result

                # Verify SCAD file was created
                scad_path = Path(result["scad_path"])
                assert scad_path.exists()
                assert "module" in result["scad_content"] or "cube" in result["scad_content"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_generate_scad_code_with_empty_project_name(self):
        """Test generate_scad_code returns error with empty project_name."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        from src.tools.modeling_tools import generate_scad_code
        result = await generate_scad_code("", {"test": "specs"})

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_generate_scad_code_with_empty_design_specs(self):
        """Test generate_scad_code returns error with empty design_specs."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["PROJECTS_DIR"] = tmpdir

            from src.tools.modeling_tools import generate_scad_code
            result = await generate_scad_code("test_project", {})

            assert result["status"] == "error"
            assert "message" in result


class TestOpenSCADCodeGeneration:
    """Tests for the enhanced OpenSCAD code generation engine."""

    @pytest.mark.asyncio
    async def test_scad_contains_parameters_section(self):
        """Test that generated SCAD contains the PARAMETERS section."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA",
                        "wall_thickness_mm": 2
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                assert "// === PARAMETERS ===" in result["scad_content"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_scad_contains_dimensions_section(self):
        """Test that generated SCAD contains the DIMENSIONS section."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA"
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                assert "// === DIMENSIONS ===" in result["scad_content"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_scad_contains_fn_parameter(self):
        """Test that generated SCAD contains the $fn parameter."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA"
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                assert "$fn" in result["scad_content"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_scad_uses_named_dimension_variables(self):
        """Test that generated SCAD uses named dimension variables."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA"
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                scad = result["scad_content"]
                assert "width =" in scad
                assert "height =" in scad
                assert "depth =" in scad
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_scad_contains_module_definition(self):
        """Test that generated SCAD contains module definition."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA"
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                assert "module " in result["scad_content"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_scad_contains_assembly_section(self):
        """Test that generated SCAD contains the ASSEMBLY section."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA"
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                assert "// === ASSEMBLY ===" in result["scad_content"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_scad_multi_part_generates_part_files(self):
        """Test that multi-part designs generate individual part files."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA"
                    },
                    "design_brief": {"name": "test"},
                    "parts": [
                        {"name": "body", "quantity": 1, "dimensions": {"width": 100, "height": 80, "depth": 60}},
                        {"name": "lid", "quantity": 1, "dimensions": {"width": 100, "height": 80, "depth": 10}}
                    ]
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                assert "part_files" in result
                assert len(result["part_files"]) == 2
                # Verify files exist
                for part_file in result["part_files"]:
                    assert Path(part_file).exists()
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_scad_generates_difference_for_hollow_box(self):
        """Test that generated SCAD uses difference() for hollow box."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                design_specs = {
                    "project_name": "test_project",
                    "specifications": {
                        "overall_dimensions": {"width": 100, "height": 80, "depth": 60},
                        "material": "PLA"
                    },
                    "design_brief": {"name": "test"}
                }

                from src.tools.modeling_tools import generate_scad_code
                result = await generate_scad_code("test_project", design_specs)

                assert result["status"] == "ok"
                assert "difference()" in result["scad_content"]
                assert "cube(" in result["scad_content"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir


class TestExportModel:
    """Tests for export_model tool."""

    @pytest.mark.asyncio
    async def test_export_model_with_valid_input_no_binary(self):
        """Test export_model returns pending status when OpenSCAD binary not found."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkeypatch the module-level constants
            import src.tools.modeling_tools as modeling_tools
            original_projects_dir = modeling_tools.PROJECTS_DIR
            original_openscad_path = modeling_tools.OPENSCAD_PATH
            modeling_tools.PROJECTS_DIR = tmpdir
            modeling_tools.OPENSCAD_PATH = "/nonexistent/openscad"

            try:
                # Create modeling directory with SCAD file
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)

                scad_file = scad_dir / "model.scad"
                scad_file.write_text("// test scad code")

                from src.tools.modeling_tools import export_model
                result = await export_model("test_project", "stl")

                assert isinstance(result, dict)
                assert "status" in result
                assert result["status"] == "pending"  # Expected when binary not found
                assert "message" in result
            finally:
                modeling_tools.PROJECTS_DIR = original_projects_dir
                modeling_tools.OPENSCAD_PATH = original_openscad_path

    @pytest.mark.asyncio
    async def test_export_model_with_empty_project_name(self):
        """Test export_model returns error with empty project_name."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        from src.tools.modeling_tools import export_model
        result = await export_model("")

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_export_model_with_invalid_format(self):
        """Test export_model returns error with invalid export_format."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["PROJECTS_DIR"] = tmpdir

            from src.tools.modeling_tools import export_model
            result = await export_model("test_project", "invalid_format")

            assert result["status"] == "error"
            assert "message" in result

    @pytest.mark.asyncio
    async def test_export_model_missing_scad_file(self):
        """Test export_model returns error when SCAD file doesn't exist."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkeypatch the PROJECTS_DIR in the module
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                # Create modeling directory but no SCAD file
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                from src.tools.modeling_tools import export_model
                result = await export_model("test_project", "stl")

                assert result["status"] == "error"
                assert "message" in result
            finally:
                modeling_tools.PROJECTS_DIR = original_dir


class TestRenderPreview:
    """Tests for render_preview tool."""

    @pytest.mark.asyncio
    async def test_render_preview_with_valid_input_no_binary(self):
        """Test render_preview returns pending status when OpenSCAD binary not found."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkeypatch the module-level constants
            import src.tools.modeling_tools as modeling_tools
            original_projects_dir = modeling_tools.PROJECTS_DIR
            original_openscad_path = modeling_tools.OPENSCAD_PATH
            modeling_tools.PROJECTS_DIR = tmpdir
            modeling_tools.OPENSCAD_PATH = "/nonexistent/openscad"

            try:
                # Create modeling directory with SCAD file
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)

                scad_file = scad_dir / "model.scad"
                scad_file.write_text("// test scad code")

                from src.tools.modeling_tools import render_preview
                result = await render_preview("test_project")

                assert isinstance(result, dict)
                assert "status" in result
                assert result["status"] == "pending"  # Expected when binary not found
                assert "message" in result
            finally:
                modeling_tools.PROJECTS_DIR = original_projects_dir
                modeling_tools.OPENSCAD_PATH = original_openscad_path

    @pytest.mark.asyncio
    async def test_render_preview_with_empty_project_name(self):
        """Test render_preview returns error with empty project_name."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        from src.tools.modeling_tools import render_preview
        result = await render_preview("")

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_render_preview_with_invalid_resolution(self):
        """Test render_preview returns error with invalid resolution."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        from src.tools.modeling_tools import render_preview
        # Resolution too high
        result = await render_preview("test_project", resolution=9999)

        assert result["status"] == "error"
        assert "message" in result
        assert "256" in result["message"] or "1024" in result["message"]

    @pytest.mark.asyncio
    async def test_render_preview_with_invalid_perspective(self):
        """Test render_preview returns error with invalid perspective names."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                # Create modeling directory with SCAD file
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)

                scad_file = scad_dir / "model.scad"
                scad_file.write_text("// test scad code")

                from src.tools.modeling_tools import render_preview
                result = await render_preview("test_project", perspectives=["invalid_view"])

                assert result["status"] == "error"
                assert "message" in result
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_render_preview_with_missing_scad_file(self):
        """Test render_preview returns error when SCAD file doesn't exist."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            modeling_tools.PROJECTS_DIR = tmpdir

            try:
                # Create modeling directory but no SCAD file
                modeling_dir = Path(tmpdir) / "test_project" / "modeling"
                modeling_dir.mkdir(parents=True, exist_ok=True)

                from src.tools.modeling_tools import render_preview
                result = await render_preview("test_project")

                assert result["status"] == "error"
                assert "message" in result
            finally:
                modeling_tools.PROJECTS_DIR = original_dir

    @pytest.mark.asyncio
    async def test_render_preview_returns_dict(self):
        """Test render_preview returns proper dict structure."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_projects_dir = modeling_tools.PROJECTS_DIR
            original_openscad_path = modeling_tools.OPENSCAD_PATH
            modeling_tools.PROJECTS_DIR = tmpdir
            modeling_tools.OPENSCAD_PATH = "/nonexistent/openscad"

            try:
                # Create modeling directory with SCAD file
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)

                scad_file = scad_dir / "model.scad"
                scad_file.write_text("// test scad code")

                from src.tools.modeling_tools import render_preview
                result = await render_preview("test_project")

                assert isinstance(result, dict)
                assert "status" in result
                assert "message" in result
            finally:
                modeling_tools.PROJECTS_DIR = original_projects_dir
                modeling_tools.OPENSCAD_PATH = original_openscad_path
