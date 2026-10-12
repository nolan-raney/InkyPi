from pathlib import Path
import shutil
from unittest.mock import Mock

from PIL import Image
from pi_heif import register_heif_opener
import pytest

from plugins.folder_photos.folder_photos import FolderPhotos, discover_photos


@pytest.fixture
def photo_folder(tmp_path):
    Image.new("RGB", (200, 100), "red").save(tmp_path / "one.JPG")
    Image.new("RGB", (100, 200), "blue").save(tmp_path / "two.png")
    return tmp_path


@pytest.fixture
def plugin():
    return FolderPhotos({"id": "folder_photos"})


def device(orientation="horizontal"):
    config = Mock()
    config.get_resolution.return_value = (80, 48)
    config.get_config.return_value = orientation
    return config


def test_discovery_ignores_hidden_partial_video_empty_and_symlink_files(photo_folder):
    (photo_folder / "empty.jpg").touch()
    (photo_folder / "live.mov").write_bytes(b"video")
    (photo_folder / ".upload.jpg").write_bytes(b"partial")
    (photo_folder / "link.jpg").symlink_to(photo_folder / "one.JPG")
    nested = photo_folder / "album"
    nested.mkdir()
    Image.new("RGB", (8, 6)).save(nested / "three.jpeg")
    hidden = photo_folder / ".partial"
    hidden.mkdir()
    Image.new("RGB", (8, 6)).save(hidden / "unfinished.jpg")
    (photo_folder / "loop").symlink_to(photo_folder, target_is_directory=True)
    assert {p.name for p in discover_photos(photo_folder)} == {"one.JPG", "two.png", "three.jpeg"}
    assert {p.name for p in discover_photos(photo_folder, recursive=False)} == {"one.JPG", "two.png"}


def test_folder_is_rescanned_and_previous_photo_does_not_repeat(photo_folder, plugin):
    settings = {"folderPath": str(photo_folder)}
    for _ in range(12):
        previous = settings.get("last_photo")
        image = plugin.generate_image(settings, device())
        assert image.size == (80, 48)
        assert settings["last_photo"] != previous
    for path in photo_folder.iterdir():
        path.unlink()
    Image.new("RGB", (10, 10), "green").save(photo_folder / "new.jpg")
    plugin.generate_image(settings, device())
    assert Path(settings["last_photo"]).name == "new.jpg"


def test_corrupt_photo_is_skipped_and_single_good_photo_can_repeat(tmp_path, plugin):
    (tmp_path / "broken.jpg").write_bytes(b"bad upload")
    good = tmp_path / "good.png"
    Image.new("RGB", (10, 10), "red").save(good)
    settings = {"folderPath": str(tmp_path), "last_photo": str(good)}
    assert plugin.generate_image(settings, device()).size == (80, 48)
    assert settings["last_photo"] == str(good)


@pytest.mark.parametrize("orientation,size", [("horizontal", (80, 48)), ("vertical", (48, 80))])
@pytest.mark.parametrize("fit", ["contain", "crop"])
def test_orientation_and_fit_modes(tmp_path, plugin, orientation, size, fit):
    Image.new("RGB", (200, 100), "red").save(tmp_path / "photo.png")
    result = plugin.generate_image({"folderPath": str(tmp_path), "fitMode": fit}, device(orientation))
    assert result.size == size
    assert result.mode == "RGB"
    assert result.getpixel((size[0] // 2, size[1] // 2)) == (255, 0, 0)
    assert result.getpixel((0, 0)) == ((255, 255, 255) if fit == "contain" else (255, 0, 0))


def test_iphone_exif_rotation(tmp_path, plugin):
    photo = Image.new("RGB", (200, 100), "red")
    exif = photo.getexif()
    exif[274] = 6
    photo.save(tmp_path / "iphone.jpg", exif=exif)
    result = plugin.generate_image({"folderPath": str(tmp_path)}, device())
    # Rotated portrait is centered with side borders, not top/bottom borders.
    assert result.getpixel((0, 24)) == (255, 255, 255)
    assert result.getpixel((40, 0))[0] > 240
    assert result.getpixel((40, 0))[1] < 15


def test_iphone_heic_photo(tmp_path, plugin):
    register_heif_opener()
    shutil.copyfile(Path(__file__).parent / "fixtures" / "portrait.heic", tmp_path / "iphone.HEIC")
    result = plugin.generate_image({"folderPath": str(tmp_path)}, device())
    assert result.size == (80, 48)
    assert result.getpixel((40, 24))[2] > 240


def test_empty_and_unavailable_folders_fail_clearly(tmp_path, plugin):
    with pytest.raises(RuntimeError, match="No photos found"):
        plugin.generate_image({"folderPath": str(tmp_path)}, device())
    with pytest.raises(RuntimeError, match="unavailable"):
        plugin.generate_image({"folderPath": str(tmp_path / "missing")}, device())


def test_removing_plugin_does_not_delete_photos(photo_folder, plugin):
    plugin.cleanup({"folderPath": str(photo_folder)})
    assert len(discover_photos(photo_folder)) == 2
