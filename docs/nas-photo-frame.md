# A NAS-backed e-ink photo frame

I wanted to upload photos from my iPhone to my existing NAS and have an e-ink frame
display them automatically. The frame also needed to keep working when the NAS or Wi-Fi
was unavailable, without adding another photo-management server.

The result runs on a Raspberry Pi Zero 2 W with a Pimoroni Inky display. TrueNAS provides
the photo dataset from a Proxmox VM. Uploads use SMB, the Pi reads through a restricted
read-only NFS export, and a background job copies images into a local cache. InkyPi
displays a random cached photo every six minutes.

## Contribution and scope

This branch extends [fatihak/InkyPi](https://github.com/fatihak/InkyPi). Upstream provides
the web UI, display integration, plugin framework, scheduling, and adaptive image loader.
I added a folder-based photo plugin, a NAS synchronization script and systemd units,
focused plugin tests, and deployment/recovery guides. The plugin reuses upstream image
loading and HEIC support rather than introducing a second decoding pipeline.

| Component | Responsibility | Implementation |
| --- | --- | --- |
| Folder Photos | Discover, select, and render local photos | [Python plugin](../src/plugins/folder_photos/folder_photos.py) |
| Photo cache sync | Mount the source and copy supported images | [Bash and rsync](../scripts/inkypi-photo-sync) |
| Background scheduling | Limit sync duration and run every five minutes | [Service](../install/inkypi-photo-sync.service), [timer](../install/inkypi-photo-sync.timer) |
| Plugin settings | Select folder, layout, and subfolder behavior | [Settings UI](../src/plugins/folder_photos/settings.html) |
| Verification | Exercise selection, formats, layout, and failure behavior | [Plugin tests](../tests/test_folder_photos.py) |

## Design decisions

**Keep display updates independent of the network.** A direct NAS read during each display
refresh would make rendering depend on network availability. Instead, systemd runs the
sync separately and the plugin reads `/var/lib/inkypi-photos`. The five-minute sync and
six-minute display intervals can be changed independently.

**Separate upload permissions from frame access.** The uploader can write through SMB;
the Pi's NFS mount is read-only and restricted to its LAN address. The cache is disposable
and can be regenerated from the NAS. A successful sync removes cached copies of images
deleted from the source, but never deletes NAS originals.

**Handle files arriving while the frame is running.** The plugin rescans on each refresh
and skips hidden files, symlinks, empty files, and unreadable images. Rsync stages transfers
and delays completed-file replacement and deletion. A source marker must exist before
sync proceeds, helping prevent an incorrect source from clearing the cache. A lock avoids
overlapping sync jobs.

**Use the Pi's existing image infrastructure.** The plugin uses InkyPi's adaptive loader
and existing HEIC decoder, honors EXIF orientation, and offers whole-photo or crop layouts.
Random selection avoids an immediate repeat when another image can be opened; if only
one readable image remains, it can repeat.

## Verified behavior

Deployment checks on October 12, 2026 covered read-only NFS access, source-to-cache
synchronization, a successful display update, and rendering from the local cache with
the NAS mount disconnected. The display and plugin intervals were subsequently verified
at 360 seconds, with the InkyPi service running.

Automated plugin tests cover file discovery, folder changes, repeat avoidance, corrupt
images, HEIC decoding, iPhone EXIF rotation, orientation, fit/crop modes, unavailable
folders, and cleanup that preserves photos. The focused plugin/image-loader suite passed
17 tests during implementation. The HEIC fixture is a synthetic image, not a personal photo.

## Limits and next steps

The sync is file-based rather than a transactional library snapshot. An interrupted
transfer can leave a mixture of old and new complete files; the next successful sync
reconciles them. An upload copied before it finishes may be unreadable until a later sync.
New uploads require connectivity even though cached photos remain usable offline.

The [fresh-Pi recovery guide](folder-photos-recovery.md) documents reconstruction from
source and private settings backups, but a full fresh-SD-card reinstall has not yet been
tested. A future validation step is to perform that recovery on a spare card. Settings
and Wi-Fi backups are point-in-time snapshots and must be refreshed after configuration
changes. This project does not provide a backup of the NAS photo library.

## Try it

Start with the [Folder Photos setup guide](../src/plugins/folder_photos/README.md).
Use the [recovery guide](folder-photos-recovery.md) for a new Pi and the
[Wi-Fi migration guide](wifi-migration.md) when changing networks. Public instructions use
example hostnames and dataset paths; credentials, live settings, and personal photos
remain outside Git.
