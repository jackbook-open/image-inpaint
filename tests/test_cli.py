from pathlib import Path

from PIL import Image

from md_image_inpaint.cli import main


def test_cli_dry_run_prints_planned_images(tmp_path: Path, capsys) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (4, 4), "blue").save(image_dir / "sample.png")
    md_path = tmp_path / "document.md"
    md_path.write_text("![sample](images/sample.png)", encoding="utf-8")

    exit_code = main([str(md_path), "--out", str(tmp_path / "output"), "--dry-run", "--verbose"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Will process: images/sample.png" in captured.out
    assert "Dry run enabled" in captured.out


def test_cli_skip_pattern_prints_skip_reason(tmp_path: Path, capsys) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (4, 4), "blue").save(image_dir / "sample.png")
    md_path = tmp_path / "document.md"
    md_path.write_text("![sample](images/sample.png)", encoding="utf-8")

    exit_code = main(
        [
            str(md_path),
            "--out",
            str(tmp_path / "output"),
            "--skip-pattern",
            "*.png",
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Will skip: images/sample.png; matched skip pattern: *.png" in captured.out
