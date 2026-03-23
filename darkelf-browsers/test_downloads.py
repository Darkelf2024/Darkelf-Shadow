from browser.downloads import safe_download_dir, randomized_filename
import os


def test_safe_download_dir_creates_folder():
    path = safe_download_dir()
    assert os.path.exists(path)
    assert "Darkelf Temp Folder" in path


def test_randomized_filename_basic():
    name = randomized_filename("file.txt")

    assert name.endswith(".txt")
    assert len(name) > len("file.txt")


def test_randomized_filename_sanitizes():
    name = randomized_filename("bad file !!!.exe")

    assert " " not in name
    assert "!" not in name
    assert name.endswith(".exe")
