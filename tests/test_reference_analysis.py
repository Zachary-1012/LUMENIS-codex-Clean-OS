"""Real generated-video full-frame measurements; not human visual acceptance."""
import csv
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import subprocess

from PIL import Image
import pytest

from lumenis.shared.content_creation import reference_analysis as reference
from lumenis.shared.content_creation import rendering
from lumenis.shared.content_creation.video_editing import VideoEditingError, fingerprint_local_media


@pytest.fixture
def source(tmp_path, monkeypatch):
    from shared_artifacts import _ffmpeg_path
    ffmpeg = _ffmpeg_path()
    if not ffmpeg or not reference._ffprobe_path():
        pytest.skip("requires the existing FFmpeg/FFprobe toolchain")
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    path = tmp_path / "reference ' ; [n].mp4"
    subprocess.run([
        ffmpeg, "-v", "error", "-nostdin", "-n", "-filter_threads", "1", "-filter_complex_threads", "1",
        "-f", "lavfi", "-i", "color=c=black:s=128x72:r=10:d=1",
        "-f", "lavfi", "-i", "color=c=white:s=128x72:r=10:d=1",
        "-f", "lavfi", "-i", "color=c=gray:s=128x72:r=10:d=1",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]", "-map", "[v]",
        "-c:v", "libx264", "-preset", "ultrafast", "-threads:v", "1", "-pix_fmt", "yuv420p", str(path),
    ], capture_output=True, check=True, timeout=30, shell=False)
    return fingerprint_local_media(str(path))


def _rows(result):
    return list(csv.DictReader(io.StringIO(result["files"]["frame-metrics.csv"].decode())))


def test_every_frame_has_real_pts_and_changes_not_just_contact_samples(source):
    before = Path(source.path).read_bytes()
    result = reference.build_reference_analysis_files(source)
    report, files = result["report"], result["files"]
    assert set(files) == {"analysis.json", "frame-metrics.csv", "shot-candidates.csv", "contact-sheet-01.png"}
    assert report == json.loads(files["analysis.json"])
    assert report["decoded_frames"] == report["ffprobe_frames"] == report["frames_analyzed"] == 30
    assert report["decode_all_frames"] == "passed"
    assert report["human_reviewed_frames"] == report["human_reviewed_contact_cells"] == 0
    assert report["ai_visual_semantics_performed"] is report["confirmed_shot_boundaries"] is False
    assert report["automatic_editing"] is report["published"] is False
    assert report["source_sha256"] == hashlib.sha256(before).hexdigest()
    assert (report["analysis_width"], report["analysis_height"]) == (128, 72)
    assert report["measurements"]["spatial_resolution_reduced"] is False
    rows = _rows(result)
    assert [int(row["frame_index"]) for row in rows] == list(range(30))
    assert [float(row["pts_sec"]) for row in rows] == pytest.approx([index / 10 for index in range(30)])
    assert rows[0]["mean_adjacent_difference"] == rows[0]["changed_area_fraction"] == ""
    assert float(rows[0]["mean_luminance"]) < .01 and float(rows[10]["mean_luminance"]) > .99
    assert float(rows[10]["mean_adjacent_difference"]) > .99
    assert float(rows[10]["changed_area_fraction"]) == 1
    assert all(float(row["edge_density"]) == 0 for row in rows)
    assert [item["frame_index"] for item in report["peak_candidates"]] == [10, 20]
    assert [item["frame_count"] for item in report["shot_candidates"]] == [10, 10, 10]
    assert sum(item["frame_count"] for item in report["shot_candidates"]) == 30
    assert report["contact_sheet"]["sample_count"] == 6 < report["frames_analyzed"]
    assert [item["frame_index"] for item in report["contact_sheet"]["cells"]] == [0, 5, 10, 15, 20, 25]
    assert all(item["human_reviewed"] is False for item in report["contact_sheet"]["cells"])
    for filename, metadata in report["outputs"].items():
        assert Path(filename).name == filename
        assert metadata["sha256"] == hashlib.sha256(files[filename]).hexdigest()
        assert metadata["size_bytes"] == len(files[filename])
    with Image.open(io.BytesIO(files["contact-sheet-01.png"])) as sheet:
        sheet.load()
        assert sheet.format == "PNG" and sheet.size == (1340, 486)
        assert sheet.getpixel((172, 125))[0] < 5
        assert sheet.getpixel((836, 125))[0] > 250
    assert source.path not in json.dumps(report)
    assert Path(source.path).read_bytes() == before
    assert reference.build_reference_analysis_files(source)["files"] == files


def test_variable_rate_pts_are_preserved_without_frame_duplication(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    path = tmp_path / "vfr.mkv"
    subprocess.run([
        _ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-i", source.path,
        "-vf", "select='lt(n,10)+not(mod(n,3))'", "-fps_mode", "vfr", "-c:v", "ffv1", "-threads:v", "1", str(path),
    ], capture_output=True, check=True, timeout=30, shell=False)
    result = reference.build_reference_analysis_files(fingerprint_local_media(str(path)))
    rows = _rows(result)
    expected_indices = list(range(10)) + [12, 15, 18, 21, 24, 27]
    assert len(rows) == result["report"]["decoded_frames"] == 16
    assert [float(row["pts_sec"]) for row in rows] == pytest.approx([index / 10 for index in expected_indices])
    deltas = [float(rows[index]["pts_sec"]) - float(rows[index - 1]["pts_sec"]) for index in range(1, len(rows))]
    assert min(deltas) == pytest.approx(.1) and max(deltas) == pytest.approx(.3)
    cells = result["report"]["contact_sheet"]["cells"]
    assert all(cell["actual_elapsed_sec"] <= cell["requested_elapsed_sec"] for cell in cells)


def test_nonzero_frame_origin_is_reported_separately_from_elapsed_sampling(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    path = tmp_path / "offset.mkv"
    subprocess.run([
        _ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-i", source.path,
        "-vf", "setpts=PTS+2/TB", "-fps_mode", "passthrough", "-c:v", "ffv1", "-threads:v", "1", str(path),
    ], capture_output=True, check=True, timeout=30, shell=False)
    result = reference.build_reference_analysis_files(fingerprint_local_media(str(path)))
    rows = _rows(result)
    assert float(rows[0]["pts_sec"]) == 2 and float(rows[0]["elapsed_sec"]) == 0
    assert result["report"]["contact_sheet"]["cells"][0]["pts_sec"] == 2
    assert result["report"]["decoded_frames"] == 30


def test_duration_limit_is_rejection_not_partial_success(source, monkeypatch):
    monkeypatch.setattr(rendering, "_run", lambda *a, **k: pytest.fail("over-limit source started a process"))
    with pytest.raises(VideoEditingError, match="REFERENCE_DURATION_LIMIT_EXCEEDED"):
        reference.build_reference_analysis_files(replace(source, duration_sec=120.01))


def test_frame_limit_sentinel_rejects_whole_task_and_cleans_raw_file(source, monkeypatch):
    monkeypatch.setattr(reference, "MAX_FRAMES", 20)
    roots = []
    original = rendering._run
    def capture(command, **kwargs):
        roots.append(kwargs["cwd"])
        return original(command, **kwargs)
    monkeypatch.setattr(rendering, "_run", capture)
    with pytest.raises(VideoEditingError, match="REFERENCE_FRAME_LIMIT_EXCEEDED"):
        reference.build_reference_analysis_files(source)
    assert roots and all(not path.exists() for path in roots)


def test_page_limit_rejects_instead_of_omitting_review_samples(source, monkeypatch):
    monkeypatch.setattr(reference, "CONTACT_CELLS_PER_PAGE", 2)
    monkeypatch.setattr(reference, "MAX_CONTACT_PAGES", 2)
    with pytest.raises(VideoEditingError, match="REFERENCE_CONTACT_PAGE_LIMIT_EXCEEDED"):
        reference.build_reference_analysis_files(source)


def test_multi_page_sheet_covers_all_half_second_targets(source, monkeypatch):
    monkeypatch.setattr(reference, "CONTACT_CELLS_PER_PAGE", 2)
    result = reference.build_reference_analysis_files(source)
    report = result["report"]
    assert report["contact_sheet"]["page_count"] == 3
    assert len(report["contact_sheet"]["cells"]) == 6
    assert {cell["filename"] for cell in report["contact_sheet"]["cells"]} == {
        "contact-sheet-01.png", "contact-sheet-02.png", "contact-sheet-03.png"}
    assert report["decoded_frames"] == 30
    for index in range(1, 4):
        with Image.open(io.BytesIO(result["files"][f"contact-sheet-{index:02d}.png"])) as sheet:
            assert sheet.size == (1340, 264)


def test_changed_fingerprint_and_nonvideo_are_rejected(source):
    with pytest.raises(VideoEditingError, match="REFERENCE_VIDEO_REQUIRED"):
        reference.build_reference_analysis_files(replace(source, has_video=False, audio_stream_count=1))
    with Path(source.path).open("ab") as output:
        output.write(b"changed")
    with pytest.raises(VideoEditingError, match="REFERENCE_SOURCE_CHANGED"):
        reference.build_reference_analysis_files(source)


def test_cancellation_is_preserved_and_private_files_removed(source, monkeypatch):
    original = rendering._run
    roots = []
    def capture(command, **kwargs):
        roots.append(kwargs["cwd"])
        return original(command, **kwargs)
    monkeypatch.setattr(rendering, "_run", capture)
    error = TimeoutError("cancel requested")
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        if calls == 25:
            raise error
    with pytest.raises(TimeoutError) as caught:
        reference.build_reference_analysis_files(source, check_cancel=cancel)
    assert caught.value is error
    assert roots and all(not root.exists() for root in roots)


def test_frame_count_mismatch_never_passes_as_full_decode(source, monkeypatch):
    original = reference._probe_json
    def truncate(command, path, **kwargs):
        result = original(command, path, **kwargs)
        if path.name == "frames.json":
            result["frames"].pop()
        return result
    monkeypatch.setattr(reference, "_probe_json", truncate)
    with pytest.raises(VideoEditingError, match="REFERENCE_FRAME_COUNT_MISMATCH"):
        reference.build_reference_analysis_files(source)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "timebase-mismatch"])
def test_bad_frame_pts_fail_closed(source, monkeypatch, kind):
    original = reference._probe_json
    def corrupt(command, path, **kwargs):
        result = original(command, path, **kwargs)
        if path.name == "frames.json":
            if kind == "missing":
                result["frames"][1].pop("pts")
            elif kind == "duplicate":
                result["frames"][1].update(pts=result["frames"][0]["pts"], pts_time=result["frames"][0]["pts_time"])
            else:
                result["frames"][1]["pts_time"] = "99.0"
        return result
    monkeypatch.setattr(reference, "_probe_json", corrupt)
    with pytest.raises(VideoEditingError, match="REFERENCE_FRAME_PTS_INVALID"):
        reference.build_reference_analysis_files(source)


def test_final_source_revalidation_prevents_mixed_source_report(source, monkeypatch):
    original = reference._contact_sheets
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        with Path(source.path).open("ab") as output:
            output.write(b"mutated during analysis")
        return result
    monkeypatch.setattr(reference, "_contact_sheets", mutate)
    with pytest.raises(VideoEditingError, match="REFERENCE_SOURCE_CHANGED"):
        reference.build_reference_analysis_files(source)


def test_real_moving_source_has_edges_and_reports_spatial_reduction(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    path = tmp_path / "moving.mp4"
    subprocess.run([
        _ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i",
        "testsrc2=size=640x360:rate=15:duration=2", "-c:v", "libx264", "-threads:v", "1", str(path),
    ], capture_output=True, check=True, timeout=30, shell=False)
    result = reference.build_reference_analysis_files(fingerprint_local_media(str(path)))
    report = result["report"]
    assert (report["analysis_width"], report["analysis_height"]) == (160, 90)
    assert report["measurements"]["spatial_resolution_reduced"] is True
    assert report["decoded_frames"] == 30
    assert all(float(row["edge_density"]) > 0 for row in _rows(result))
    assert any(float(row["mean_adjacent_difference"] or 0) > 0 for row in _rows(result))


def test_real_multi_video_input_requires_selection_not_silent_first_stream(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    path = tmp_path / "multiple.mkv"
    subprocess.run([_ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-i", source.path,
                    "-map", "0:v:0", "-map", "0:v:0", "-c:v", "copy", str(path)],
                   capture_output=True, check=True, timeout=30, shell=False)
    with pytest.raises(VideoEditingError, match="REFERENCE_SINGLE_VIDEO_STREAM_REQUIRED"):
        reference.build_reference_analysis_files(fingerprint_local_media(str(path)))


def test_actual_7200_frames_accepted_and_7201_rejected_without_truncated_pass(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    for count in (7200, 7201):
        path = tmp_path / f"boundary-{count}.mp4"
        subprocess.run([
            _ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i",
            "color=c=blue:s=16x16:r=61", "-frames:v", str(count), "-c:v", "libx264",
            "-preset", "ultrafast", "-threads:v", "1", str(path),
        ], capture_output=True, check=True, timeout=30, shell=False)
        asset = fingerprint_local_media(str(path))
        assert asset.duration_sec < 120
        if count == 7201:
            with pytest.raises(VideoEditingError, match="REFERENCE_FRAME_LIMIT_EXCEEDED"):
                reference.build_reference_analysis_files(asset)
        else:
            result = reference.build_reference_analysis_files(asset)
            assert result["report"]["decoded_frames"] == result["report"]["frames_analyzed"] == 7200
            assert len(_rows(result)) == 7200
            assert result["report"]["contact_sheet"]["page_count"] == 10
            assert result["report"]["human_reviewed_frames"] == 0


def test_permission_style_value_error_callback_is_not_relabeled_as_bad_pts(source, monkeypatch):
    original = reference._probe_json
    ready = False
    def capture(command, path, **kwargs):
        nonlocal ready
        result = original(command, path, **kwargs)
        if path.name == "frames.json":
            ready = True
        return result
    monkeypatch.setattr(reference, "_probe_json", capture)
    error = ValueError("source permission revoked")
    def check():
        if ready:
            raise error
    with pytest.raises(ValueError) as caught:
        reference.build_reference_analysis_files(source, check_cancel=check)
    assert caught.value is error


def test_peak_limit_is_explicit_and_shot_rows_still_cover_all_frames():
    rows = [{"frame_index": index, "pts": index, "pts_sec": index / 30,
             "elapsed_sec": index / 30, "frame_duration_sec": 1 / 30,
             "mean_adjacent_difference": None if index == 0 else 1,
             "changed_area_fraction": None if index == 0 else 1} for index in range(300)]
    peaks, shots, observed = reference._peaks_and_shots(rows)
    assert observed == 299 and len(peaks) == reference.MAX_PEAK_CANDIDATES == 128
    assert sum(shot["frame_count"] for shot in shots) == 300
    assert shots[0]["first_frame_index"] == 0 and shots[-1]["last_frame_index"] == 299
