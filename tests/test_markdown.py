from pathlib import Path

from md_image_inpaint.markdown import build_tasks, parse_markdown_images


def test_parse_local_remote_and_missing_images(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    local_image = image_dir / "sample.png"
    local_image.write_bytes(b"not-a-real-image")
    absolute_image = image_dir / "absolute.png"
    absolute_image.write_bytes(b"not-a-real-image")
    md_path = tmp_path / "doc.md"
    md_text = "\n".join(
        [
            f"![absolute]({absolute_image})",
            "![relative](images/sample.png)",
            "![remote](https://example.com/image.png)",
            "![missing](images/missing.png)",
        ]
    )
    md_path.write_text(md_text, encoding="utf-8")

    refs = parse_markdown_images(md_text, md_path)

    assert len(refs) == 4
    assert refs[0].resolved_path == absolute_image.resolve()
    assert refs[0].exists is True
    assert refs[1].resolved_path == local_image.resolve()
    assert refs[1].exists is True
    assert refs[2].is_remote is True
    assert refs[2].resolved_path is None
    assert refs[3].exists is False


def test_build_tasks_records_skip_reasons(tmp_path: Path) -> None:
    md_path = tmp_path / "doc.md"
    md_text = "![remote](https://example.com/a.png)\n![missing](nope.png)"
    md_path.write_text(md_text, encoding="utf-8")

    tasks = build_tasks(md_text, md_path)

    assert [task.should_process for task in tasks] == [False, False]
    assert tasks[0].reason == "remote image skipped"
    assert tasks[1].reason == "local image does not exist"
