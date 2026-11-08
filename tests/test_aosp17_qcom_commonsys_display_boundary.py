#!/usr/bin/env python3
"""Android 17 PE-Reborn stage 193: historical Qualcomm display-commonsys source boundary.

Platform-source-only CI: never imports any device tree, requires no vendor blobs,
and never implies a compiled/booted Android 17 image.
"""
from pathlib import Path
import os
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "11253d91e0b79c976479215ce78a942e4718817d"
ARCHIVE_TREE = "b14f3873e1b308dc4276b135321accf4b23e5a42"
OLD_PATH = "vendor/qcom/opensource/commonsys/display"
OLD_NAME = "vendor_qcom_opensource_commonsys_display"
INTF_PATH = "vendor/qcom/opensource/commonsys-intf/display"


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True,
        capture_output=True, text=True
    ).stdout.strip()


def entry(revision, path):
    found = git("ls-tree", revision, "--", path)
    if not found:
        raise AssertionError("missing Git object " + path)
    metadata, returned_path = found.split("\t", 1)
    if returned_path != path:
        raise AssertionError("path mismatch " + returned_path)
    mode, kind, sha = metadata.split()
    return mode, kind, sha


def pinned_source(key):
    name = os.environ.get(key)
    if not name or not Path(name).is_file():
        raise AssertionError("missing immutable input: " + key)
    return Path(name).read_text(encoding="utf-8")


class ArchivedQcomDisplayCommonsysTest(unittest.TestCase):
    def test_upstream_history_untouched(self):
        p = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
             ARCHIVE_COMMIT, "HEAD"], capture_output=True, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE_COMMIT + "^{tree}"), ARCHIVE_TREE)

    def test_git_trees_and_original_soong_module_objects(self):
        # Protect historical code. New tests/docs/CI never touch original contents.
        fixed = {
            "Android.bp": ("100644", "blob", "ad6d5eb9a2a8c577758a988cbc5192390db4b85b"),
            "config": ("040000", "tree", "b3e54f2fd5c0360c7ba4144881324b8eba4be16f"),
            "gralloc": ("040000", "tree", "170fac2dba9434779b41ac55a9bff8ac6dd6a36b"),
            "libqdmetadata": ("040000", "tree", "62a638586c5b2d2fd939f50a6cc7e5c8020ab2c4"),
            "services": ("040000", "tree", "f63a6967c0646e4cd6661820e7ba87f644e25156"),
        }
        for path, original in fixed.items():
            with self.subTest(path=path):
                self.assertEqual(entry("HEAD", path), original)
                self.assertEqual(entry("HEAD", path), entry(ARCHIVE_COMMIT, path))

    def test_repo_only_contains_three_runtime_compatibility_shims(self):
        files = (
            "gralloc/Android.bp",
            "libqdmetadata/Android.bp",
            "services/config/src/Android.bp",
        )
        modules = []
        for f in files:
            content = (ROOT / f).read_text(encoding="utf-8")
            self.assertIn("cc_library_shared", content)
            self.assertIn("system_ext_specific: true", content)
            modules.extend(re.findall(r'\bname:\s*"([^"]+)"', content))
        self.assertEqual(modules, [
            "libgralloc.system.qti",
            "libqdMetaData.system",
            "libdisplayconfig.system.qti",
        ])
        # No HWC3 IComposer service, allocator or SDM sources here.
        for path in ("composer", "composer3", "sdm", "sde-drm", "aidl",
                     "device.mk", "BoardConfig.mk", "AndroidProducts.mk"):
            self.assertFalse((ROOT / path).exists())

    def test_gralloc_is_hidl_mapper4_not_aidl_or_native_stable_c(self):
        bp = (ROOT / "gralloc/Android.bp").read_text(encoding="utf-8")
        c = (ROOT / "gralloc/QtiGralloc.cpp").read_text(encoding="utf-8")
        self.assertIn('"android.hardware.graphics.mapper@4.0"', bp)
        self.assertIn('"libhidlbase"', bp)
        self.assertIn("graphics::mapper::V4_0::IMapper", c)
        self.assertIn("IMapper::getService()", c)
        self.assertIn("mapper->get(", c)
        self.assertIn("mapper->set(", c)
        self.assertNotIn('"libimapper_stablec"', bp)

    def test_metadata_shim_depends_on_old_mapper_layout(self):
        bp = (ROOT / "libqdmetadata/Android.bp").read_text(encoding="utf-8")
        src = (ROOT / "libqdmetadata/qdMetaData.cpp").read_text(encoding="utf-8")
        self.assertIn('"libgralloc.system.qti"', bp)
        self.assertIn('"libhidlbase"', bp)
        self.assertIn('"display_intf_headers"', bp)
        self.assertIn("private_handle_t::validate(handle)", src)
        self.assertIn("handle->fd_metadata", src)
        self.assertIn("reinterpret_cast<MetaData_t *>(handle->base_metadata)", src)

    def test_display_config_bridge_uses_hidl_2_0(self):
        bp = (ROOT / "services/config/src/Android.bp").read_text(encoding="utf-8")
        c = (ROOT / "services/config/src/client_impl.cpp").read_text(encoding="utf-8")
        self.assertIn('"vendor.display.config@2.0"', bp)
        self.assertIn('"libhidlbase"', bp)
        self.assertIn("IDisplayConfig::tryGetService()", c)
        self.assertIn("display_config_->perform(", c)
        self.assertNotIn("vendor.qti.hardware.display.config-V12-ndk", bp)

    def test_old_soong_namespace_imports_other_unqualified_pe_archive(self):
        root = (ROOT / "Android.bp").read_text(encoding="utf-8")
        self.assertIn("soong_namespace", root)
        self.assertIn(f'"{INTF_PATH}"', root)
        self.assertNotIn("cc_library_shared", root)
        self.assertNotIn("aidl_interface", root)

    def test_product_mk_packages_compatibility_libraries_not_service(self):
        mk = (ROOT / "config/display-product-commonsys.mk").read_text(encoding="utf-8")
        for name in (
            "libdisplayconfig.system.qti",
            "libgralloc.system.qti",
            "libdisplayconfig.system", "libdrm",
            "liblayerext.qti", "libsmomoconfig.qti", "libcomposerextn.qti"
        ):
            with self.subTest(package=name):
                self.assertIn(name, mk)
        self.assertIn("SOONG_CONFIG_qtidisplaycommonsys_displayextension", mk)
        self.assertIn("SOONG_CONFIG_qtidisplaycommonsys_composer3ext", mk)
        # This archive defines only three of the listed runtime libraries.
        # Other product dependencies might be supplied elsewhere, but not here.

    def test_clean_aosp17_official_graph_owns_graphics(self):
        root = ET.fromstring(pinned_source("PE_AOSP17_REFERENCE"))
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        projects = {p.get("path"): p.get("name") for p in root.iter("project")}
        self.assertEqual(projects["hardware/interfaces"], "platform/hardware/interfaces")
        self.assertNotIn(OLD_PATH, projects)
        self.assertNotIn(INTF_PATH, projects)
        self.assertNotIn(OLD_NAME, projects.values())

    def test_current_platform_entrypoint_never_enabled_old_display(self):
        root = ET.fromstring(pinned_source("PE_AOSP17_DEFAULT"))
        self.assertEqual(
            [i.get("name") for i in root.findall("include")],
            ["aosp17_pe_p2_kernel_configs.xml"],
        )
        self.assertFalse(any(
            p.get("path") in (OLD_PATH, INTF_PATH) or p.get("name") == OLD_NAME
            for p in root.iter("project")
        ))

    def test_new_hwc3_candidate_requires_different_library_and_aidl(self):
        modern = pinned_source("PE_QCOM_HWC3_COMPOSER_BP")
        self.assertIn('"libgralloc.qti"', modern)
        self.assertIn('"libdisplayconfig.qti"', modern)
        self.assertIn('"vendor.qti.hardware.display.config-V12-ndk"', modern)
        self.assertIn('"android.hardware.graphics.composer3-V3-ndk"', modern)
        self.assertNotIn('"libgralloc.system.qti"', modern)
        self.assertNotIn('"libdisplayconfig.system.qti"', modern)
        # This is ONLY a source-level contrast, not proof of Soong closure.

    def test_no_device_tree_or_features_are_implemented_in_this_stage(self):
        for path in ("device.mk", "BoardConfig.mk", "AndroidProducts.mk",
                     "aidl", "composer", "sdm", "sde-drm", "init.mondrian.rc"):
            self.assertFalse((ROOT / path).exists())
        # CI has no dependency on LF52406/LineageOS device trees or blobs.

if __name__ == "__main__":
    unittest.main(verbosity=2)
