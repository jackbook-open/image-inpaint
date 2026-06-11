from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from md_image_inpaint.desktop import (
    RUNTIME_ENV_VAR,
    check_environment,
    clear_model_cache,
    default_output_dir,
    human_summary,
    resolve_iopaint_command,
)
from md_image_inpaint.models import CancelToken


def test_default_output_dir_uses_document_name_and_timestamp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("md_image_inpaint.desktop.default_output_parent", lambda: tmp_path / "Outputs")

    output = default_output_dir(tmp_path / "My Demo.md", datetime(2026, 6, 8, 9, 10, 11))

    assert output == tmp_path / "Outputs" / "My-Demo-20260608-091011"


def test_clear_model_cache_recreates_empty_directory(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "old.bin").write_text("old", encoding="utf-8")

    cleared = clear_model_cache(cache)

    assert cleared == cache.resolve()
    assert cache.exists()
    assert list(cache.iterdir()) == []


def test_check_environment_can_skip_iopaint_requirement() -> None:
    result = check_environment(iopaint_cmd="definitely-not-installed-iopaint", require_iopaint=False)

    assert result.ok is True
    assert "passed" in result.user_message
    assert any("Model cache free space" in line for line in result.details)
    assert any("First processing run may download" in line for line in result.details)
    assert any("progress and retry details" in line for line in result.details)


def test_check_environment_reports_low_model_cache_space(monkeypatch) -> None:
    monkeypatch.setattr("md_image_inpaint.desktop._free_bytes", lambda _path: 128 * 1024 * 1024)

    result = check_environment(iopaint_cmd="definitely-not-installed-iopaint", require_iopaint=False)

    assert result.ok is False
    assert any("free model cache space" in line for line in result.details)
    assert any("first-run model preparation" in line for line in result.details)


def test_check_environment_reports_missing_required_iopaint() -> None:
    result = check_environment(iopaint_cmd="definitely-not-installed-iopaint", require_iopaint=True)

    assert result.ok is False
    assert any("IOPaint runtime" in line for line in result.details)


def test_resolve_iopaint_command_prefers_runtime_env(tmp_path: Path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    command = runtime / ("iopaint.cmd")
    command.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setenv(RUNTIME_ENV_VAR, str(runtime))

    assert resolve_iopaint_command("definitely-not-installed-iopaint") == str(command.resolve())


def test_human_summary_is_user_readable() -> None:
    assert human_summary(2, 3, 1) == "Processed 2; skipped 3; failed 1."


def test_cancel_token_records_cancellation() -> None:
    token = CancelToken()

    assert token.cancelled is False
    token.cancel()
    assert token.cancelled is True


def test_windows_build_includes_user_installer() -> None:
    project_root = Path(__file__).resolve().parents[1]
    installer_dir = project_root / "packaging" / "windows"
    build_script = (project_root / "packaging" / "build-windows.ps1").read_text(encoding="utf-8")
    install_smoke = (project_root / "packaging" / "verify-windows-install-smoke.ps1").read_text(encoding="utf-8")
    installer_smoke = (project_root / "packaging" / "verify-windows-installer-smoke.ps1").read_text(encoding="utf-8")
    zip_smoke = (project_root / "packaging" / "verify-windows-zip-smoke.ps1").read_text(encoding="utf-8")
    spec_text = (project_root / "packaging" / "pyinstaller-image-inpaint.spec").read_text(encoding="utf-8")
    inno_script = (installer_dir / "ImageInpaint.iss").read_text(encoding="utf-8")
    install_script = (installer_dir / "install-user.ps1").read_text(encoding="utf-8")
    uninstall_script = (installer_dir / "uninstall-user.ps1").read_text(encoding="utf-8")
    package_readme = (installer_dir / "README-FIRST.txt").read_text(encoding="utf-8")

    assert (installer_dir / "Install Image Inpaint.cmd").exists()
    assert (installer_dir / "install-user.ps1").exists()
    assert (installer_dir / "Uninstall Image Inpaint.cmd").exists()
    assert (installer_dir / "uninstall-user.ps1").exists()
    assert (installer_dir / "README-FIRST.txt").exists()
    assert (installer_dir / "ImageInpaint.iss").exists()
    assert "Double-click Install Image Inpaint.cmd" in package_readme
    assert "authorized to modify" in package_readme
    assert "README-FIRST.txt" in install_script
    assert "IMAGE_INPAINT_INSTALL_LOCALAPPDATA" in install_script
    assert "IMAGE_INPAINT_INSTALL_LOCALAPPDATA" in uninstall_script
    assert "robocopy" in install_script
    assert "robocopy" in uninstall_script
    assert "$global:LASTEXITCODE = 0" in install_script
    assert "$global:LASTEXITCODE = 0" in uninstall_script
    assert "packaging\\windows" in build_script
    assert "Installer" in build_script
    assert "Resolve-InnoSetupCompiler" in build_script
    assert "ImageInpaint-Setup-x64.exe" in build_script
    assert "verify-windows-installer-smoke.ps1" in build_script
    assert "Inno Setup compiler was not found" in build_script
    assert "verify-windows-install-smoke.ps1" in build_script
    assert "verify-windows-zip-smoke.ps1" in build_script
    assert "Write Windows checksum" in build_script
    assert "verify-checksum.py" in build_script
    assert "--write" in build_script
    assert "$ZipPath.sha256" in build_script
    assert "Windows install smoke passed" in install_smoke
    assert "ImageInpaintInstallSmoke" in install_smoke
    assert "LaunchSmoke" in install_smoke
    assert "RequireIopaint" in install_smoke
    assert "ImageInpaintSmoke.exe" in install_smoke
    assert "Windows installed app launch smoke failed" in install_smoke
    assert "/VERYSILENT" in installer_smoke
    assert "/SUPPRESSMSGBOXES" in installer_smoke
    assert "/DIR=$InstallDir" in installer_smoke
    assert "ImageInpaintSmoke.exe" in installer_smoke
    assert "Windows installer smoke passed" in installer_smoke
    assert "RequireIopaint" in installer_smoke
    assert "OutputBaseFilename=ImageInpaint-Setup-x64" in inno_script
    assert "PrivilegesRequired=lowest" in inno_script
    assert "DefaultDirName={localappdata}\\ImageInpaint\\app" in inno_script
    assert "recursesubdirs createallsubdirs" in inno_script
    assert "ImageInpaint.exe" in inno_script
    assert "-LaunchSmoke" in build_script
    assert "-RequireIopaint" in build_script
    assert "OpenRead($ResolvedZipPath)" in zip_smoke
    assert "verify-checksum.py" in zip_smoke
    assert "Windows zip checksum verification failed" in zip_smoke
    assert "ExtractToDirectory($ResolvedZipPath.ProviderPath, $ExtractDir)" in zip_smoke
    assert "FullExtract" in zip_smoke
    assert "ZipFile" in zip_smoke
    assert "--smoke-check" in zip_smoke
    assert "--require-iopaint" in zip_smoke
    assert "RequireIopaint" in zip_smoke
    assert "if ($RequireIopaint)" in zip_smoke
    assert "verify-windows-install-smoke.ps1" in zip_smoke
    assert "-LaunchSmoke" in zip_smoke
    assert "Windows zip smoke passed" in zip_smoke
    assert "ImageInpaintSmoke" in build_script
    assert "ImageInpaintSmoke" in spec_text
    assert "console=True" in spec_text


def test_macos_build_creates_drag_install_dmg_layout() -> None:
    project_root = Path(__file__).resolve().parents[1]
    build_script = (project_root / "packaging" / "build-macos.sh").read_text(encoding="utf-8")
    verify_script = (project_root / "packaging" / "verify-release-macos.sh").read_text(encoding="utf-8")
    dmg_smoke = (project_root / "packaging" / "verify-macos-dmg-smoke.sh").read_text(encoding="utf-8")
    install_smoke = (project_root / "packaging" / "verify-macos-install-smoke.sh").read_text(encoding="utf-8")
    spec_text = (project_root / "packaging" / "pyinstaller-image-inpaint.spec").read_text(encoding="utf-8")
    entitlements = (project_root / "packaging" / "macos-entitlements.plist").read_text(encoding="utf-8")

    assert "DMG_ROOT=\"dist/dmg-root\"" in build_script
    assert "ln -s /Applications" in build_script
    assert "README.txt" in build_script
    assert "Drag ImageInpaint.app to Applications" in build_script
    assert "ImageInpaintSmoke" in build_script
    assert "packaging/macos-entitlements.plist" in build_script
    assert "verify-checksum.py --write \"$DMG_PATH\"" in build_script
    assert "$DMG_PATH.sha256" in build_script
    assert "macos-entitlements.plist" in spec_text
    assert "entitlements_file=str(macos_entitlements)" in spec_text
    assert "com.apple.security.cs.disable-library-validation" in entitlements
    assert "ImageInpaintSmoke" in verify_script
    assert "macOS release verification must run on macOS" in verify_script
    assert "packaging/macos-entitlements.plist" in verify_script
    assert "hdiutil verify" in dmg_smoke
    assert "verify-checksum.py" in dmg_smoke
    assert "hdiutil attach" in dmg_smoke
    assert "hdiutil detach" in dmg_smoke
    assert "mount | grep" not in dmg_smoke
    assert "ImageInpaint.app" in dmg_smoke
    assert "Applications" in dmg_smoke
    assert "--smoke-check" in dmg_smoke
    assert "--require-iopaint" in dmg_smoke
    assert "macOS install smoke must run on macOS" in install_smoke
    assert "hdiutil attach" in install_smoke
    assert "hdiutil detach" in install_smoke
    assert "verify-checksum.py" in install_smoke
    assert "mount | grep" not in install_smoke
    assert "cp -R \"$MOUNT_POINT/ImageInpaint.app\"" in install_smoke
    assert "APPLICATIONS_DIR" in install_smoke
    assert "--smoke-check --require-iopaint" in install_smoke


def test_ci_runs_packaged_process_smoke_on_each_desktop_package() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workflow = (project_root / ".github" / "workflows" / "desktop-package.yml").read_text(encoding="utf-8")
    windows_smoke = (project_root / "packaging" / "verify-packaged-process-smoke.ps1").read_text(encoding="utf-8")
    macos_smoke = (project_root / "packaging" / "verify-packaged-process-smoke.sh").read_text(encoding="utf-8")
    development = (project_root / "docs" / "DEVELOPMENT.md").read_text(encoding="utf-8")

    assert "Verify Windows packaged process smoke" in workflow
    assert ".\\packaging\\verify-packaged-process-smoke.ps1" in workflow
    assert "Verify Windows zip smoke" in workflow
    assert ".\\packaging\\verify-windows-zip-smoke.ps1" in workflow
    assert "Install Inno Setup" in workflow
    assert "choco install innosetup" in workflow
    assert ".\\packaging\\build-windows.ps1 -NoIopaint -Installer" in workflow
    assert "ImageInpaint-Setup-x64.exe" in workflow
    assert "ImageInpaint-Setup-x64.exe.sha256" in workflow
    assert "Verify Windows checksum" in workflow
    assert "python packaging/verify-checksum.py ${{ matrix.artifact_path }}" in workflow
    assert "macos-arm64" in workflow
    assert "macos-intel" in workflow
    assert "macos-15" in workflow
    assert "macos-15-intel" in workflow
    assert "macos-15` for Apple Silicon" in development
    assert "macos-15-intel` for Intel" in development
    assert "Do not collapse these to `macos-latest`" in development
    assert "ImageInpaint-macOS-arm64" in workflow
    assert "ImageInpaint-macOS-intel" in workflow
    assert "Verify macOS packaged process smoke" in workflow
    assert "bash packaging/verify-packaged-process-smoke.sh" in workflow
    assert "Verify macOS dmg smoke" in workflow
    assert "bash packaging/verify-macos-dmg-smoke.sh" in workflow
    assert "Verify macOS install smoke" in workflow
    assert "bash packaging/verify-macos-install-smoke.sh" in workflow
    assert "Verify macOS checksum" in workflow
    assert "${{ matrix.artifact_path }}.sha256" in workflow
    assert "--process-smoke" in windows_smoke
    assert "--process-smoke" in macos_smoke
    assert "IMAGE_INPAINT_RUNTIME_DIR" in windows_smoke
    assert "IMAGE_INPAINT_RUNTIME_DIR" in macos_smoke
    assert "bash ./packaging/make-fake-iopaint-runtime.sh" in macos_smoke


def test_real_runtime_release_workflow_runs_platform_verifiers() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workflow = (project_root / ".github" / "workflows" / "desktop-real-runtime.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch" in workflow
    assert "prepare-iopaint-runtime-windows.ps1" in workflow
    assert "prepare-iopaint-runtime-macos.sh" in workflow
    assert "build-windows.ps1 -RuntimeDir" in workflow
    assert "build-windows.ps1 -RuntimeDir .runtime\\iopaint -PythonCommand python -Installer" in workflow
    assert "build-macos.sh --runtime-dir" in workflow
    assert "verify-release-windows.ps1" in workflow
    assert "verify-windows-zip-smoke.ps1" in workflow
    assert "Verify Windows checksum" in workflow
    assert "verify-release-macos.sh" in workflow
    assert "verify-macos-dmg-smoke.sh" in workflow
    assert "verify-macos-dmg-smoke.sh --require-iopaint" in workflow
    assert "verify-macos-install-smoke.sh --require-iopaint" in workflow
    assert "ImageInpaint-Windows-x64-real-runtime" in workflow
    assert "ImageInpaint-Setup-x64.exe" in workflow
    assert "ImageInpaint-Setup-x64.exe.sha256" in workflow
    assert "choco install innosetup" in workflow
    assert "macos-arm64" in workflow
    assert "macos-intel" in workflow
    assert "macos-15" in workflow
    assert "macos-15-intel" in workflow
    assert "ImageInpaint-macOS-arm64-real-runtime" in workflow
    assert "ImageInpaint-macOS-intel-real-runtime" in workflow
    assert "notarize_macos" in workflow
    assert "sign-notarize-macos.sh" in workflow
    assert "verify-checksum.py --write release/ImageInpaint-macOS.dmg" in workflow
    assert "python packaging/verify-checksum.py release/ImageInpaint-macOS.dmg" in workflow
    assert "${{ matrix.artifact_path }}.sha256" in workflow
    assert "APPLE_DEVELOPER_ID_APPLICATION" in workflow
    assert "APPLE_APP_SPECIFIC_PASSWORD" in workflow


def test_release_evidence_template_tracks_user_ready_requirements() -> None:
    project_root = Path(__file__).resolve().parents[1]
    template = (project_root / "docs" / "RELEASE_EVIDENCE_TEMPLATE.md").read_text(encoding="utf-8")
    checklist = (project_root / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    development = (project_root / "docs" / "DEVELOPMENT.md").read_text(encoding="utf-8")

    assert "verify-repository-boundaries.py" in template
    assert "python -m pytest -q" in template
    assert "artifact SHA256" in template
    assert "Windows setup artifact" in template
    assert "artifact checksum uploaded" in template
    assert "Desktop real runtime release" in template
    assert "verify-release-windows.ps1" in template
    assert "verify-windows-installer-smoke.ps1 -RequireIopaint" in template
    assert "verify-windows-zip-smoke.ps1 -FullExtract" in template
    assert "Manual smoke checklist used: `docs/MANUAL_USER_SMOKE.md`" in template
    assert "Opened without Python, terminal, or dependency installation" in template
    assert "download/install" in template
    assert "Optional install/uninstall smoke result" in template
    assert "macOS Apple Silicon" in template
    assert "macOS Intel" in template
    assert "verify-release-macos.sh" in template
    assert "verify-macos-dmg-smoke.sh --require-iopaint" in template
    assert "verify-macos-install-smoke.sh --require-iopaint" in template
    assert "sign-notarize-macos.sh" in template
    assert "xcrun stapler validate" in template
    assert "spctl --assess --type open" in template
    assert "Non-developer user smoke tester" in template
    assert "Time from download" in template
    assert "Original Markdown unchanged" in template
    assert "Responsible-Use Evidence" in template
    assert "RELEASE_EVIDENCE_TEMPLATE.md" in checklist
    assert "RELEASE_EVIDENCE_TEMPLATE.md" in development


def test_acceptance_matrix_maps_goal_to_required_evidence() -> None:
    project_root = Path(__file__).resolve().parents[1]
    matrix = (project_root / "docs" / "ACCEPTANCE_MATRIX.md").read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    checklist = (project_root / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "Windows users can download and start without Python" in matrix
    assert "ImageInpaint-Setup-x64.exe" in matrix
    assert "verify-windows-installer-smoke.ps1" in matrix
    assert "macOS Apple Silicon users can open a dmg/app" in matrix
    assert "macOS Intel users can open a dmg/app" in matrix
    assert "Signed and notarized dmg" in matrix
    assert "GUI supports the normal user workflow" in matrix
    assert "Runtime checks and first-run model behavior" in matrix
    assert "Original files are not modified" in matrix
    assert "Pre-check/dry-run" in matrix
    assert "Errors are human-readable" in matrix
    assert "Responsible use is visible" in matrix
    assert "CLI remains available" in matrix
    assert "Dependency/runtime boundaries are clean" in matrix
    assert "Release artifacts are complete and verifiable" in matrix
    assert "Documentation covers users and developers" in matrix
    assert "Automated tests and local Windows evidence are not enough" in matrix
    assert "ACCEPTANCE_MATRIX.md" in readme
    assert "ACCEPTANCE_MATRIX.md" in checklist


def test_manual_user_smoke_checklist_covers_non_developer_flows() -> None:
    project_root = Path(__file__).resolve().parents[1]
    smoke = (project_root / "docs" / "MANUAL_USER_SMOKE.md").read_text(encoding="utf-8")
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    checklist = (project_root / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    matrix = (project_root / "docs" / "ACCEPTANCE_MATRIX.md").read_text(encoding="utf-8")

    assert "Do not install Python" in smoke
    assert "Do not open a terminal" in smoke
    assert "Time the flow" in smoke
    assert "Windows Smoke" in smoke
    assert "ImageInpaint-Setup-x64.exe" in smoke
    assert "ImageInpaint-Windows-x64.zip" in smoke
    assert "desktop or Start menu shortcut" in smoke
    assert "Optional install smoke" in smoke
    assert "macOS Apple Silicon Smoke" in smoke
    assert "macOS Intel Smoke" in smoke
    assert "Gatekeeper result" in smoke
    assert "Click `Pre-check`" in smoke
    assert "Click `Start processing`" in smoke
    assert "Open output" in smoke
    assert "Open result document" in smoke
    assert "View log" in smoke
    assert "Error Message Spot Checks" in smoke
    assert "missing local image" in smoke
    assert "remote image" in smoke
    assert "Mask dimensions do not match" in smoke
    assert "Responsible-use language" in smoke
    assert "MANUAL_USER_SMOKE.md" in readme
    assert "MANUAL_USER_SMOKE.md" in checklist
    assert "MANUAL_USER_SMOKE.md" in matrix


def test_macos_sign_notarize_script_uses_hardened_runtime_and_stapling() -> None:
    project_root = Path(__file__).resolve().parents[1]
    script = (project_root / "packaging" / "sign-notarize-macos.sh").read_text(encoding="utf-8")

    assert "ENTITLEMENTS_PATH" in script
    assert "macos-entitlements.plist" in script
    assert "codesign --force --deep --options runtime --timestamp --entitlements" in script
    assert "xcrun notarytool submit" in script
    assert "--wait" in script
    assert "submit_for_notarization" in script
    assert "mapfile" not in script
    assert "readarray" not in script
    assert "xcrun stapler staple" in script
    assert "xcrun stapler validate" in script
    assert "verify-checksum.py --write \"$SIGNED_DMG_PATH\"" in script
    assert "$SIGNED_DMG_PATH.sha256" in script
    assert "APPLE_NOTARY_KEYCHAIN_PROFILE" in script
    assert "APPLE_ID" in script
    assert "APPLE_TEAM_ID" in script
    assert "APPLE_APP_SPECIFIC_PASSWORD" in script


def test_macos_shell_scripts_stay_bash_32_and_bsd_userland_compatible() -> None:
    project_root = Path(__file__).resolve().parents[1]
    scripts = sorted((project_root / "packaging").glob("*.sh"))
    forbidden_literals = [
        "mapfile",
        "readarray",
        "declare -A",
        "local -n",
        "coproc",
        "&>>",
        "realpath",
        "readlink -f",
        "grep -P",
        "sed -r",
        "sort -V",
        "xargs -r",
        "stat -c",
        "cp -a",
        "install -D",
        "mktemp --tmpdir",
    ]
    forbidden_regexes = [
        re.compile(r"\$\{[^}]+,,[^}]*\}"),
        re.compile(r"\$\{[^}]+\^\^[^}]*\}"),
    ]

    assert scripts
    for script_path in scripts:
        script = script_path.read_text(encoding="utf-8")
        assert "set -euo pipefail" in script, script_path.name
        for literal in forbidden_literals:
            assert literal not in script, f"{script_path.name} uses {literal}"
        for pattern in forbidden_regexes:
            assert not pattern.search(script), f"{script_path.name} uses Bash 4 case conversion"


def test_iopaint_runtime_scripts_preflight_python_and_imports() -> None:
    project_root = Path(__file__).resolve().parents[1]
    windows_script = (project_root / "packaging" / "prepare-iopaint-runtime-windows.ps1").read_text(encoding="utf-8")
    macos_script = (project_root / "packaging" / "prepare-iopaint-runtime-macos.sh").read_text(encoding="utf-8")

    assert "Assert-CompatiblePython" in windows_script
    assert "Assert-RuntimeImports" in windows_script
    assert "Python 3.10, 3.11, or 3.12" in windows_script
    assert "import torch" in windows_script
    assert 'metadata.version("iopaint")' in windows_script
    assert "assert_compatible_python" in macos_script
    assert "assert_runtime_imports" in macos_script
    assert "Python 3.10, 3.11, or 3.12" in macos_script
    assert "import torch" in macos_script
    assert 'metadata.version("iopaint")' in macos_script
