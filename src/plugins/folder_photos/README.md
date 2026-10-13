# Folder Photos

Display random photos from a local folder. The folder is rescanned on every refresh, so
new photos appear automatically. With multiple readable photos, the immediately previous
photo is avoided. A corrupt or disappearing file is skipped; an empty/unreadable collection
raises an error and InkyPi retains the existing display image.

Supports JPEG, PNG, HEIC/HEIF, WebP, and TIFF using InkyPi's existing decoder and adaptive
image loader. iPhone EXIF rotation is honored. Live Photo videos are ignored; the still
image is displayed. Hidden files, incomplete rsync files, empty files, and symlinks are
ignored. Choose full-photo layout with white borders or a cropped full-screen layout.
Removing the plugin from a playlist does not delete photos.

For a replacement Pi or SD card, follow the [fresh-Pi recovery guide](../../../docs/folder-photos-recovery.md).

## NAS photo frame

Use the local cache `/var/lib/inkypi-photos` as the plugin's photo folder. A separate
`inkypi-photo-sync` systemd timer synchronizes a read-only NAS mount every five minutes.
Display refreshes never access the network, so cached photos remain available while the
NAS is off. Set InkyPi's refresh interval to 6 minutes (or another desired interval).

1. Prepare a dedicated TrueNAS photo dataset/share. Allow the uploader to write via SMB
   and the Pi to read via a dedicated read-only NFS export restricted to its LAN address.
   Create an empty `.inkypi-photo-source` marker file at the export root. Do not change the
   existing Jellyfin NFS export or recursively modify existing storage ACLs.
2. Install `nfs-common` and `rsync` on the Pi. Create `/mnt/inkypi-photos` and
   `/var/lib/inkypi-photos`.
3. Configure an explicit read-only mount in `/etc/fstab`, using the verified export path:

   ```text
   nas.example.local:/mnt/example-pool/InkyPhotos /mnt/inkypi-photos nfs ro,noauto,soft,timeo=50,retrans=2,nosuid,nodev,noexec 0 0
   ```

   Replace `nas.example.local` and `/mnt/example-pool/InkyPhotos` with your server and
   verified export path before use. `noauto` avoids delaying boot;
   the sync job mounts it on demand. `soft` limits retries for this read-only photo source;
   it is not a recommended option for writable storage. The service also has a two-minute
   timeout. Do not mount the remote share directly at the local cache path.
4. Install the sync files:

   ```bash
   sudo install -m 755 scripts/inkypi-photo-sync /usr/local/bin/inkypi-photo-sync
   sudo install -m 644 install/inkypi-photo-sync.service /etc/systemd/system/
   sudo install -m 644 install/inkypi-photo-sync.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now inkypi-photo-sync.timer
   sudo systemctl start inkypi-photo-sync.service
   ```

5. Check `journalctl -u inkypi-photo-sync.service` and the cache, then add **Folder Photos**
   to a playlist. Keep existing photo playlists until the new source has been tested.

The cache belongs to this sync job. Successful syncs remove cached copies deleted from the
NAS, but never remove NAS originals. A missing source marker stops sync before rsync runs.
Rsync delays completed-file replacement and deletion until the end; I/O errors skip deletion
by default. Hidden staging files are excluded from the slideshow. An interrupted sync can
leave a mix of old and new complete files; the next successful sync reconciles them. Copying
an upload still in progress can produce an unreadable cached file, which the plugin skips
until the next sync replaces it.

## Upload from iPhone

On the home LAN, open Files → Browse → menu → Connect to Server, enter
`smb://nas.example.local`, and sign in using the existing SMB upload account. Select the photo
share. In Photos, select images → Share → Save to Files → that share. Originals are kept
on TrueNAS; the Pi caches them locally. A fresh upload normally reaches the cache on the
next five-minute sync and the screen on the next display refresh.

No cloud account or additional photo-management server is required.

## Development checks

Run `PYTHONPATH=src python -m pytest tests/test_folder_photos.py tests/test_image_loader.py`.
`tests/fixtures/portrait.heic` is a synthetic solid-blue portrait generated solely as a
decoder test fixture; it contains no personal photo data. Production needs only the
existing `pi-heif` dependency. The encoder used to create this fixture is not required
to run tests or operate the plugin.
