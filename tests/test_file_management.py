"""Tests for file management tools (TICKET-025)."""

import os
import json
import zipfile
from pathlib import Path
import pytest
from src.config import PROJECTS_DIR
from src.tools.coordinator_tools import (
    get_project_structure,
    organize_project_files,
    create_design_version,
    list_design_versions,
    backup_project,
    export_project,
)
from src.tools.coordinator_tools import create_project_session


@pytest.mark.asyncio
async def test_get_project_structure_valid():
    """Test get_project_structure returns file listing for valid project."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    # Create a project first
    project_name = "test_get_structure_valid"
    result = await create_project_session(project_name=project_name)
    assert result["status"] == "ok"

    # Get structure
    result = await get_project_structure(project_name=project_name)

    assert result["status"] == "ok"
    assert result["project_name"] == project_name
    assert "root_path" in result
    assert "files" in result
    assert isinstance(result["files"], list)
    assert result["total_files"] >= 0
    assert result["total_size_bytes"] >= 0


@pytest.mark.asyncio
async def test_get_project_structure_empty_project_name():
    """Test get_project_structure returns error for empty project_name."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    result = await get_project_structure(project_name="")

    assert result["status"] == "error"
    assert "message" in result
    assert "required" in result["message"].lower()


@pytest.mark.asyncio
async def test_get_project_structure_nonexistent_project():
    """Test get_project_structure returns error for nonexistent project."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    result = await get_project_structure(project_name="nonexistent_project_xyz_123")

    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_organize_project_files_creates_missing_dirs():
    """Test organize_project_files creates missing directory structure."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_organize_creates_dirs"
    await create_project_session(project_name=project_name)

    # Remove a directory to test creation
    project_path = Path(PROJECTS_DIR) / project_name
    design_sketches = project_path / "design" / "sketches"
    if design_sketches.exists():
        import shutil
        shutil.rmtree(design_sketches)

    # Now organize
    result = await organize_project_files(project_name=project_name)

    assert result["status"] == "ok"
    assert result["project_name"] == project_name
    assert len(result["directories_created"]) > 0
    assert "sketches" in str(result["directories_created"])


@pytest.mark.asyncio
async def test_organize_project_files_idempotent():
    """Test organize_project_files is idempotent (existing dirs not recreated)."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_organize_idempotent"
    await create_project_session(project_name=project_name)

    # First call
    result1 = await organize_project_files(project_name=project_name)
    assert result1["status"] == "ok"
    created_count_1 = len(result1["directories_created"])

    # Second call should show existing dirs
    result2 = await organize_project_files(project_name=project_name)
    assert result2["status"] == "ok"
    existing_count_2 = len(result2["existing_directories"])
    assert existing_count_2 >= created_count_1


@pytest.mark.asyncio
async def test_organize_project_files_empty_name():
    """Test organize_project_files returns error for empty project_name."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    result = await organize_project_files(project_name="")

    assert result["status"] == "error"
    assert "required" in result["message"].lower()


@pytest.mark.asyncio
async def test_create_design_version_creates_snapshot():
    """Test create_design_version creates a snapshot directory with files."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_design_version_snapshot"
    await create_project_session(project_name=project_name)

    # Create some design files
    project_path = Path(PROJECTS_DIR) / project_name
    design_path = project_path / "design"
    test_file = design_path / "test.txt"
    test_file.write_text("test content")

    # Create version
    result = await create_design_version(project_name=project_name, version_label="Test Version")

    assert result["status"] == "ok"
    assert "version_id" in result
    assert result["label"] == "Test Version"
    assert "timestamp" in result
    assert result["files_versioned"] > 0

    # Verify snapshot directory exists
    version_path = design_path / "versions" / result["version_id"]
    assert version_path.exists()
    assert (version_path / "test.txt").exists()


@pytest.mark.asyncio
async def test_list_design_versions_returns_versions():
    """Test list_design_versions returns the created versions."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    import uuid
    project_name = f"test_list_versions_{uuid.uuid4().hex[:8]}"
    await create_project_session(project_name=project_name)

    # Create versions
    await create_design_version(project_name=project_name, version_label="v1")
    await create_design_version(project_name=project_name, version_label="v2")

    # List versions
    result = await list_design_versions(project_name=project_name)

    assert result["status"] == "ok"
    assert result["project_name"] == project_name
    assert len(result["versions"]) == 2
    assert result["total_versions"] == 2
    assert result["versions"][0]["label"] == "v1"
    assert result["versions"][1]["label"] == "v2"


@pytest.mark.asyncio
async def test_backup_project_creates_backup():
    """Test backup_project creates a backup directory with files."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_backup_creates"
    await create_project_session(project_name=project_name)

    # Create some files
    project_path = Path(PROJECTS_DIR) / project_name
    design_file = project_path / "design" / "test_file.txt"
    design_file.write_text("test design")

    # Backup project
    result = await backup_project(project_name=project_name)

    assert result["status"] == "ok"
    assert "backup_id" in result
    assert "timestamp" in result
    assert result["files_backed_up"] > 0
    assert "backup_path" in result

    # Verify backup directory exists
    backup_path = Path(result["backup_path"])
    assert backup_path.exists()


@pytest.mark.asyncio
async def test_backup_project_excludes_backups_dir():
    """Test backup_project doesn't create nested backups."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_backup_no_nesting"
    await create_project_session(project_name=project_name)

    # Create first backup
    result1 = await backup_project(project_name=project_name)
    assert result1["status"] == "ok"
    files_in_first = result1["files_backed_up"]

    # Create second backup (should not include first backup)
    result2 = await backup_project(project_name=project_name)
    assert result2["status"] == "ok"

    # Second backup shouldn't have nested backup directories
    backup_path = Path(result2["backup_path"])
    has_backups_dir = any(
        item.is_dir() and item.name == "backups"
        for item in backup_path.rglob("*")
    )
    assert not has_backups_dir, "Backup directory should not contain nested backups"


@pytest.mark.asyncio
async def test_export_project_creates_zip():
    """Test export_project creates a valid zip file."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_export_zip"
    await create_project_session(project_name=project_name)

    # Create some files
    project_path = Path(PROJECTS_DIR) / project_name
    test_file = project_path / "design" / "export_test.txt"
    test_file.write_text("export test content")

    # Export project
    result = await export_project(project_name=project_name, export_format="zip")

    assert result["status"] == "ok"
    assert "export_path" in result
    assert result["file_count"] > 0
    assert result["size_bytes"] > 0

    # Verify zip file exists and is valid
    export_path = Path(result["export_path"])
    assert export_path.exists()
    assert export_path.suffix == ".zip"

    # Verify it's a valid zip file
    with zipfile.ZipFile(export_path, "r") as zipf:
        names = zipf.namelist()
        assert len(names) > 0


@pytest.mark.asyncio
async def test_export_project_invalid_format():
    """Test export_project returns error for unsupported format."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_export_invalid_format"
    await create_project_session(project_name=project_name)

    result = await export_project(project_name=project_name, export_format="tar")

    assert result["status"] == "error"
    assert "unsupported" in result["message"].lower()


@pytest.mark.asyncio
async def test_export_project_excludes_backups():
    """Test export_project excludes backups and exports directories."""
    os.environ["ANTHROPIC_API_KEY"] = "test_key"

    project_name = "test_export_excludes_backups"
    await create_project_session(project_name=project_name)

    # Create backup first
    await backup_project(project_name=project_name)

    # Export
    result = await export_project(project_name=project_name, export_format="zip")
    assert result["status"] == "ok"

    # Verify zip doesn't contain backups directory
    export_path = Path(result["export_path"])
    with zipfile.ZipFile(export_path, "r") as zipf:
        names = zipf.namelist()
        has_backups = any("backups" in name for name in names)
        has_exports = any("exports" in name for name in names)
        assert not has_backups, "Export should not contain backups directory"
        assert not has_exports, "Export should not contain exports directory"
