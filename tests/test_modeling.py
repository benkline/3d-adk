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

    def test_modeling_agent_has_four_tools(self):
        """Test that modeling agent has four tools."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        from src.agents.modeling import modeling_agent
        assert len(modeling_agent.tools) == 4

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


class TestExportModel:
    """Tests for export_model tool."""

    @pytest.mark.asyncio
    async def test_export_model_with_valid_input_no_binary(self):
        """Test export_model returns pending status when OpenSCAD binary not found."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            original_openscad = modeling_tools.OPENSCAD_PATH
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
                modeling_tools.PROJECTS_DIR = original_dir
                modeling_tools.OPENSCAD_PATH = original_openscad

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
            original_openscad = modeling_tools.OPENSCAD_PATH
            modeling_tools.PROJECTS_DIR = tmpdir
            modeling_tools.OPENSCAD_PATH = "/bin/sh"

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
                modeling_tools.OPENSCAD_PATH = original_openscad


class TestExportModelMultiPart:
    """Tests for multi-part export functionality."""

    @pytest.mark.asyncio
    async def test_export_model_multi_part_no_binary(self):
        """Test export_model multi-part returns pending when OpenSCAD binary not found."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkeypatch the module-level constants
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            original_openscad = modeling_tools.OPENSCAD_PATH
            modeling_tools.PROJECTS_DIR = tmpdir
            modeling_tools.OPENSCAD_PATH = "/nonexistent/openscad"

            try:
                # Create multi-part SCAD files
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)
                (scad_dir / "base.scad").write_text("// base")
                (scad_dir / "lid.scad").write_text("// lid")

                from src.tools.modeling_tools import export_model
                result = await export_model("test_project", "stl", parts=["base", "lid"])

                assert result["status"] == "pending"
                assert "message" in result
            finally:
                modeling_tools.PROJECTS_DIR = original_dir
                modeling_tools.OPENSCAD_PATH = original_openscad

    @pytest.mark.asyncio
    async def test_export_model_multi_part_missing_scad(self):
        """Test export_model returns error when part SCAD files are missing."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            original_dir = modeling_tools.PROJECTS_DIR
            original_openscad = modeling_tools.OPENSCAD_PATH
            modeling_tools.PROJECTS_DIR = tmpdir
            modeling_tools.OPENSCAD_PATH = "/bin/sh"

            try:
                # Create only one part's SCAD file
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)
                (scad_dir / "base.scad").write_text("// base")
                # Missing: lid.scad

                from src.tools.modeling_tools import export_model
                result = await export_model("test_project", "stl", parts=["base", "lid"])

                assert result["status"] == "error"
                assert "message" in result
                assert "lid" in result["message"]
            finally:
                modeling_tools.PROJECTS_DIR = original_dir
                modeling_tools.OPENSCAD_PATH = original_openscad

    @pytest.mark.asyncio
    async def test_export_model_multi_part_invalid_parts_list(self):
        """Test export_model returns error with empty parts list."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        from src.tools.modeling_tools import export_model
        result = await export_model("test_project", "stl", parts=[])

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_export_model_single_file_validation_empty_file(self):
        """Test export_model returns error when exported file is empty."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            import subprocess
            original_dir = modeling_tools.PROJECTS_DIR
            original_openscad = modeling_tools.OPENSCAD_PATH
            original_run = subprocess.run

            modeling_tools.PROJECTS_DIR = tmpdir
            # Set OPENSCAD_PATH to something that exists
            modeling_tools.OPENSCAD_PATH = "/bin/sh"

            try:
                # Create SCAD file
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)
                (scad_dir / "model.scad").write_text("// test")

                # Mock subprocess.run to create empty output file
                def mock_run_empty(cmd, **kwargs):
                    # Find the output file and create empty file
                    for i, arg in enumerate(cmd):
                        if arg == "-o" and i + 1 < len(cmd):
                            Path(cmd[i + 1]).write_text("")  # Empty file
                            break
                    return subprocess.CompletedProcess(cmd, 0, b"", b"")

                subprocess.run = mock_run_empty

                from src.tools.modeling_tools import export_model
                result = await export_model("test_project", "stl")

                # Should fail because file is empty
                assert result["status"] == "error"
                assert "message" in result
                assert "empty" in result["message"].lower() or "invalid" in result["message"].lower()
            finally:
                modeling_tools.PROJECTS_DIR = original_dir
                modeling_tools.OPENSCAD_PATH = original_openscad
                subprocess.run = original_run

    @pytest.mark.asyncio
    async def test_export_model_multi_part_returns_export_paths_list(self):
        """Test export_model multi-part returns export_paths list and parts list."""
        os.environ["ANTHROPIC_API_KEY"] = "test_key"

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.tools.modeling_tools as modeling_tools
            import subprocess
            original_dir = modeling_tools.PROJECTS_DIR
            original_openscad = modeling_tools.OPENSCAD_PATH
            original_run = subprocess.run

            modeling_tools.PROJECTS_DIR = tmpdir
            modeling_tools.OPENSCAD_PATH = "/bin/sh"

            try:
                # Create SCAD files for parts
                scad_dir = Path(tmpdir) / "test_project" / "modeling" / "scad"
                scad_dir.mkdir(parents=True, exist_ok=True)
                (scad_dir / "base.scad").write_text("// base")
                (scad_dir / "lid.scad").write_text("// lid")

                # Mock subprocess to create non-empty files
                def mock_run(cmd, **kwargs):
                    # Find the output file and create it with content
                    for i, arg in enumerate(cmd):
                        if arg == "-o" and i + 1 < len(cmd):
                            Path(cmd[i + 1]).write_text("dummy model data")
                            break
                    return subprocess.CompletedProcess(cmd, 0, b"", b"")

                subprocess.run = mock_run

                from src.tools.modeling_tools import export_model
                result = await export_model("test_project", "stl", parts=["base", "lid"])

                assert result["status"] == "ok"
                assert "export_paths" in result
                assert isinstance(result["export_paths"], list)
                assert len(result["export_paths"]) == 2
                assert "parts" in result
                assert result["parts"] == ["base", "lid"]
                assert result["export_format"] == "stl"
            finally:
                subprocess.run = original_run
                modeling_tools.PROJECTS_DIR = original_dir
                modeling_tools.OPENSCAD_PATH = original_openscad
