from PIL import Image, ImageDraw

from charlora.data.curate import apply_report, curate_directory


def _save_quadrant(path, quadrant, size=(64, 64)):
    # phash is a grayscale/DCT structural hash, so plain solid colors all
    # collapse to ~identical hashes regardless of hue. Use a distinguishing
    # spatial pattern instead: a white square in one quadrant on a black
    # background, so different quadrants land far apart in hash space while
    # the same quadrant at a different size lands close together.
    im = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(im)
    w, h = size
    boxes = {
        "top_left": (0, 0, w // 2, h // 2),
        "bottom_right": (w // 2, h // 2, w, h),
    }
    draw.rectangle(boxes[quadrant], fill=(255, 255, 255))
    im.save(path)


def _save(path, color, size=(32, 32)):
    Image.new("RGB", size, color).save(path)


def test_curate_directory_detects_duplicates_and_keeps_higher_res(tmp_path):
    # Two near-identical images (same pattern, different size) plus one distinct image.
    _save_quadrant(tmp_path / "1.jpg", "top_left", size=(128, 128))
    _save_quadrant(tmp_path / "2.jpg", "top_left", size=(32, 32))
    _save_quadrant(tmp_path / "3.jpg", "bottom_right", size=(32, 32))

    report = curate_directory(tmp_path, threshold=4)

    assert report.total == 3
    assert report.corrupt == []
    assert len(report.duplicate_groups) == 1
    group = report.duplicate_groups[0]
    assert {p.name for p in group} == {"1.jpg", "2.jpg"}
    assert group[0].name == "1.jpg"  # higher-resolution kept first


def test_curate_directory_flags_corrupt_file(tmp_path):
    _save(tmp_path / "good.jpg", (0, 255, 0))
    (tmp_path / "bad.jpg").write_bytes(b"not an image")

    report = curate_directory(tmp_path, threshold=4)

    assert len(report.corrupt) == 1
    assert report.corrupt[0].name == "bad.jpg"


def test_apply_report_moves_rejects_and_sidecar_json(tmp_path):
    _save(tmp_path / "1.jpg", (255, 0, 0), size=(64, 64))
    _save(tmp_path / "2.jpg", (255, 0, 0), size=(32, 32))
    (tmp_path / "2.json").write_text("{}")

    report = curate_directory(tmp_path, threshold=4)
    apply_report(report, tmp_path)

    assert not (tmp_path / "2.jpg").exists()
    assert not (tmp_path / "2.json").exists()
    assert (tmp_path / "_rejected" / "2.jpg").exists()
    assert (tmp_path / "_rejected" / "2.json").exists()
    assert (tmp_path / "1.jpg").exists()  # kept image untouched
