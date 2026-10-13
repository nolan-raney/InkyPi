# Reinstall the NAS photo frame on a fresh Pi

The code is saved in `nolan-raney/InkyPi`, branch **feature/nas-photo-frame**. GitHub stores
the application/plugin/sync code and these instructions. Photos, live device settings, and
credentials are not committed to Git. The NAS photo share is the source of the pictures;
the Pi's local cache can be rebuilt. This procedure assumes the NAS dataset and shares
still exist. Restoring a lost NAS pool requires a separate data backup.

This is a reconstruction guide based on the deployed installation and its verified mount,
sync and display behavior; a fresh SD-card reinstall has not been performed as a test.

## 1. Prepare the Pi

Install a supported 64-bit Raspberry Pi OS, configure Wi-Fi and SSH, and use the desired
hostname/user (the existing device uses `npr-inky` and `nolan`). The deployment runs Debian
13/Trixie on a Pi Zero 2 W with a Pimoroni Inky display. Keep the same display hardware.

Give the Pi a DHCP reservation, or update the TrueNAS photo NFS share's authorized host to
its new LAN IP. The current deployment authorizes **192.168.50.62**. A new IP without an
updated authorization will produce an NFS access-denied error.

For multiple home networks, new access points, or restoring saved Wi-Fi profiles, see
[Wi-Fi recovery and migration](wifi-migration.md).

## 2. Install the fork, including our plugin

On the fresh Pi:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone --branch feature/nas-photo-frame --single-branch https://github.com/nolan-raney/InkyPi.git ~/InkyPi
cd ~/InkyPi
sudo bash install/install.sh
```

Accept the installer's reboot prompt and reconnect afterward. For the existing Pimoroni
Inky display, no Waveshare `-W` argument is needed. This installs the normal InkyPi service,
Python dependencies, and the Folder Photos code. It does not yet install our NAS mount/timer.

## 3. Reconnect the photo source

The current photo dataset is `HomeLab-DataP1/InkyPhotos` at
`/mnt/HomeLab-DataP1/InkyPhotos`, shared as SMB **InkyPhotos** and read-only NFS. The export
maps the Pi to the NAS user `nolan`. Keep the `.inkypi-photo-source` marker at its root.

```bash
sudo apt-get install -y nfs-common rsync
sudo mkdir -p /mnt/inkypi-photos /var/lib/inkypi-photos
sudoedit /etc/fstab
```

Add the following entry **once**, verifying that the server and export path are still valid:

```text
192.168.50.153:/mnt/HomeLab-DataP1/InkyPhotos /mnt/inkypi-photos nfs ro,noauto,soft,timeo=50,retrans=2,nosuid,nodev,noexec 0 0
```

Then install and test the background job:

```bash
cd ~/InkyPi
sudo install -m 755 scripts/inkypi-photo-sync /usr/local/bin/inkypi-photo-sync
sudo install -m 644 install/inkypi-photo-sync.service /etc/systemd/system/
sudo install -m 644 install/inkypi-photo-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start inkypi-photo-sync.service
sudo systemctl enable --now inkypi-photo-sync.timer
sudo find /var/lib/inkypi-photos -type f
```

The first sync repopulates the cache from the NAS. Run cache inspection with sudo because
synced subfolders can be root-owned and inaccessible to an unprivileged listing. Do not
mount the NAS over the cache directory: the two paths must remain separate for offline use.

If sync fails, inspect `sudo journalctl -u inkypi-photo-sync.service -n 30 --no-pager`.
Check the authorized Pi IP, dataset permissions, export path and source marker. Do not
expand NFS authorization to the whole LAN merely to bypass an IP mismatch.

## 4. Restore settings or configure the slideshow

A private settings backup can be stored on the NAS as
`InkyPhotos/.recovery/inkypi-settings-latest.tar.gz`. It contains `src/config/device.json`,
an optional `.env` file, and a recovery manifest. It is a point-in-time snapshot, not an
automatic continuously updated backup. The sync job excludes this hidden directory.

After the source is mounted, restore settings on the **fresh installation with the same
display hardware**:

```bash
sudo systemctl stop inkypi
sudo install -d -m 700 ~/inky-recovery-backups
sudo cp ~/InkyPi/src/config/device.json ~/inky-recovery-backups/device.json.before-restore
sudo chmod 600 ~/inky-recovery-backups/device.json.before-restore
sudo tar -xzf /mnt/inkypi-photos/.recovery/inkypi-settings-latest.tar.gz -C ~/InkyPi src/config/device.json
sudo systemctl start inkypi
```

If the backup includes `.env` and you need its API settings, restore that member separately
with the service stopped and protect it with mode 600. The NAS slideshow needs no API keys.
Keep this archive, `.env`, and live device JSON out of Git. The image cache is intentionally
not backed up because it is regenerated from the NAS.

Without a settings backup, open InkyPi's web UI and:

1. Set the device refresh interval to **6 minutes**, preserving the desired timezone,
   orientation and image settings.
2. Add **Folder Photos** to an all-day playlist, with photo folder
   `/var/lib/inkypi-photos`, **Fit whole photo**, and subfolders enabled.
3. Set its playlist refresh interval to **6 minutes** and display the instance once to test.

The cache checks the NAS every five minutes; the display rotates every 6 minutes. Existing
NAS photos do not need to be uploaded again. iPhone uploads still go to Files →
`smb://192.168.50.153` → Registered User → **InkyPhotos**.

## 5. Verify recovery

```bash
sudo systemctl is-active inkypi
sudo systemctl is-enabled inkypi-photo-sync.timer
sudo systemctl show inkypi-photo-sync.service -p Result -p ExecMainStatus
curl --fail --output /dev/null http://127.0.0.1/plugin/folder_photos
```

Confirm the photos appear in the local cache and a photo displays on the frame. Cached
photos continue rotating during a NAS outage; new uploads arrive after connectivity returns.
Reinstalling the Pi does not require deleting/recreating the NAS dataset or shares.
