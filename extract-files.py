#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

import extract_utils.tools
import os

extract_utils.tools.DEFAULT_PATCHELF_VERSION = '0_9'

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

namespace_imports = [
    'device/xiaomi/violet',
    'hardware/qcom-caf/sm8150',
    'hardware/qcom-caf/wlan',
    'hardware/xiaomi',
    'vendor/qcom/opensource/commonsys/display',
    'vendor/qcom/opensource/commonsys-intf/display',
    'vendor/qcom/opensource/dataservices',
    'vendor/qcom/opensource/display',
]

def lib_fixup_vendor_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}_{partition}' if partition == 'vendor' else None

lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    (
        'com.qualcomm.qti.dpm.api@1.0',
        'libmmosal',
        'vendor.qti.hardware.fm@1.0',
        'vendor.qti.imsrtpservice@3.0',
    ): lib_fixup_vendor_suffix,
}

blob_fixups: blob_fixups_user_type = {
    'vendor/lib/libwvhidl.so':
        blob_fixup().replace_needed('libcrypto.so', 'libcrypto-v34.so'),
    'vendor/lib/mediadrm/libwvdrmengine.so':
        blob_fixup().replace_needed('libcrypto.so', 'libcrypto-v34.so'),
    'vendor/lib64/libwvhidl.so':
        blob_fixup().replace_needed('libcrypto.so', 'libcrypto-v34.so'),
    'vendor/lib64/mediadrm/libwvdrmengine.so':
        blob_fixup().replace_needed('libcrypto.so', 'libcrypto-v34.so'),
    'vendor/lib64/libvidhance.so':
        blob_fixup().add_needed('libdemangle.so')
                    .add_needed('libcomparetf2.so'),
    'vendor/lib64/camera/components/com.vidhance.node.eis.so':
        blob_fixup().add_needed('libdemangle.so')
                    .add_needed('libcomparetf2.so')
                    .replace_needed('libui.so', 'libui-v34.so'),
    'vendor/lib64/camera/components/com.vidhance.stats.aec_dmbr.so':
        blob_fixup().add_needed('libcomparetf2.so'),
    'vendor/lib64/hw/camera.qcom.so':
        blob_fixup().binary_regex_replace(b'libc\\+\\+.so', b'libc29.so'),
    'vendor/bin/mlipayd@1.1':
        blob_fixup().remove_needed('vendor.xiaomi.hardware.mtdservice@1.0.so'),
    'vendor/lib64/libmlipay.so':
        blob_fixup().remove_needed('vendor.xiaomi.hardware.mtdservice@1.0.so'),
    'vendor/lib64/libmlipay@1.1.so':
        blob_fixup().remove_needed('vendor.xiaomi.hardware.mtdservice@1.0.so'),
    'system_ext/lib64/libwfdnative.so':
        blob_fixup().remove_needed('android.hidl.base@1.0.so'),
    'system_ext/lib/libwfdnative.so':
        blob_fixup().remove_needed('android.hidl.base@1.0.so'),
    'vendor/lib64/libgoodixhwfingerprint.so':
        blob_fixup().remove_needed('android.hidl.base@1.0.so'),
    'vendor/etc/camera/camxoverridesettings.txt':
        blob_fixup().regex_replace(r'0x10080', '0')
                    .regex_replace(r'0x1F', '0x0'),
    'vendor/lib64/libvendor.goodix.hardware.interfaces.biometrics.fingerprint@2.1.so': 
        blob_fixup().remove_needed('libhidlbase.so')
                    .binary_regex_replace(b'libhidltransport.so', 'libhidlbase-v32.so\x00'),
    'vendor/lib64/mediadrm/libwvdrmengine.so':
        blob_fixup().replace_needed('libprotobuf-cpp-lite-3.9.1.so', 'libprotobuf-cpp-full-3.9.1.so'),
    'vendor/lib/mediadrm/libwvdrmengine.so':
        blob_fixup().replace_needed('libprotobuf-cpp-lite-3.9.1.so', 'libprotobuf-cpp-full-3.9.1.so'),
    'vendor/lib64/libwvhidl.so':
        blob_fixup().replace_needed('libprotobuf-cpp-lite-3.9.1.so', 'libprotobuf-cpp-full-3.9.1.so'),
}

module = ExtractUtilsModule(
    'violet',
    'xiaomi',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
)

# --- Cleanup Unlisted Blobs ---
ANDROID_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
PROP_DIR = os.path.join(ANDROID_ROOT, "vendor/xiaomi/violet/proprietary")
PROP_FILES_TXT = os.path.join(os.path.dirname(__file__), "proprietary-files.txt")

def get_expected_files():
    """Read proprietary-files.txt and return a set of expected file paths, ignoring SHA1SUM values and metadata."""
    expected_files = set()
    
    if not os.path.exists(PROP_FILES_TXT):
        print(f"Warning: {PROP_FILES_TXT} not found.")
        return expected_files

    with open(PROP_FILES_TXT, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # Ignore empty lines and comments
            
            # Extract part before | (to remove SHA1SUM) and before ; (to remove metadata)
            file_paths = line.split("|")[0].split(";")[0]

            # Split multiple paths by ':'
            for path in file_paths.split(":"):
                expected_files.add(path.lstrip("-"))  # Remove leading '-' if present

    return expected_files

def cleanup_unlisted_blobs():
    """Remove unlisted blobs from the proprietary folder."""
    if not os.path.exists(PROP_DIR):
        return

    expected_files = get_expected_files()

    for root, _, files in os.walk(PROP_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, PROP_DIR)

            # Ignore .part files silently
            if ".part" in file:
                continue

            if rel_path not in expected_files:
                print(f"Removing unlisted blob: {file_path}")
                os.remove(file_path)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
    cleanup_unlisted_blobs()  # Run cleanup after extraction
