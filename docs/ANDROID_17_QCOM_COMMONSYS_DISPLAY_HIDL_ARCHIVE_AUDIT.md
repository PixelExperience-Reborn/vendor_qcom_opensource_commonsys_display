# Stage 193 — Qualcomm display-commonsys archived HIDL compatibility shims

**PE-Reborn Android 17, 2026-11-08. Scope: standalone AOSP 17 platform restoration and source dependency graph.** No device-tree implementation, no feature work, and no reuse of LF52406/LineageOS source trees. SM8475/mondrian-specific device adaptation is a **later** phase.

## Historical archive provenance and original purpose

- Repository: https://github.com/PixelExperience-Reborn/vendor_qcom_opensource_commonsys_display
- PixelExperience historical branch: seventeen. Original HEAD **11253d91e0b79c976479215ce78a942e4718817d** (2024-01-04); original Git tree **b14f3873e1b308dc4276b135321accf4b23e5a42**. Original CLO merge tag: **LA.QSSI.14.0.r1-11200-qssi.0** (2024 Qualcomm/QSSI14). Change includes private gralloc buffer-dequeue-duration metadata support. History and original source subtree object IDs are preserved.
- **19 original source files**, contained under root Android.bp, gralloc, libqdmetadata, services/config/src and product config. It is a small compatibility **library** set, **not** a full Qualcomm Composer HAL, SDM/DRM source, Stable-C mapper implementation, Android product definition, or replacement AOSP graphics stack.
- The original historical repo is still useful to understand how previous Qualcomm developers bridged Gralloc4 metadata and a vendor display-config interface. Do **not** claim it establishes Android17 compatibility or compiled output.

## Exact Soong/source dependency analysis

The root Android.bp defines a Soong namespace whose only import is **vendor/qcom/opensource/commonsys-intf/display**. That is a *separate historical repo*, audited at stage 192 and not selected for the clean AOSP17 source graph. These old source trees have to be considered together to understand unresolved dependencies, but **neither is imported** into current default.xml.

The archive defines exactly these three system_ext shared-library modules:

1. **libgralloc.system.qti** (gralloc/Android.bp): explicitly shared_libs **android.hardware.graphics.mapper@4.0** and **libhidlbase**, with source QtiGralloc.cpp using **graphics::mapper::V4_0::IMapper**, **IMapper::getService()** and HIDL metadata get/set. It is **not** an AIDL allocator or native Mapper Stable-C V5 provider.
2. **libqdMetaData.system** (libqdmetadata/Android.bp): depends on **libgralloc.system.qti**, libgralloctypes, libhidlbase, and imported **display_intf_headers**. Implementation accesses **private_handle_t**, **fd_metadata**, mmap metadata; ABI/layout compatibility with a newer mapper is not established.
3. **libdisplayconfig.system.qti** (services/config/src/Android.bp): requires **vendor.display.config@2.0** (old HIDL) and libhidlbase; client uses **IDisplayConfig::tryGetService()** and **perform(...)**, not QTI Stable AIDL display.config V12.

The historical config/display-product-commonsys.mk additionally packages **libdisplayconfig.system**, **libdrm**, **liblayerext.qti**, **libsmomoconfig.qti** and **libcomposerextn.qti**. Those modules have **no definition in this archived repository**. They may be supplied by other sources, but cannot be assumed present in a complete, clean AOSP17 graph. Makefile switches **SOONG_CONFIG_qtidisplaycommonsys_displayextension** and **composer3ext** for QCOM products. These are build-policy choices in the historic product and are **not** added or changed in PE-Reborn.

## Modern platform decision (do not confuse component generations)

Official independently pinned Google **android-17.0.0_r1** provides **hardware/interfaces** and AOSP-owned graphics HAL API definitions. The source-only *nondefault* Qualcomm-derived HWC3 candidate (Sony-hosted commit **baf61f736e2109522e3f72754ee7cfacbfa2dc6c**) references **libgralloc.qti**, **libdisplayconfig.qti**, **vendor.qti.hardware.display.config-V12-ndk**, and Android **Composer3 V2/V3 AIDL**. These are *not* identical to historic system_ext libraries **libgralloc.system.qti**, **libdisplayconfig.system.qti**, or old HIDL **vendor.display.config@2.0**.

Enabling the 2024 compatibility libraries merely because they have Qualcomm provenance would import deprecated HIDL client dependencies and a not-yet-validated Soong namespace. Switching to modern AIDL requires its own compatible provider graph, not renaming a HIDL library or blindly including a newer branch. Future graphics code choices are separate from the present task: the platform first needs a reproducible clean source graph and successful Soong/Make builds.

**Stage 193 decision:** preserve historical archive and license; **exclude it from active AOSP17 manifest** and block accidental path/alias source reintroduction in all staged and nondefault candidate manifest resolutions. This does **not** prohibit modern Qualcomm code with separately verified ownership and dependencies.

## Implemented in stage 193

- Original Git commit/trees preserved. Add 12 source-only tests verifying original Git objects, precisely defined Soong modules, HIDL mapper@4.0 and vendor.display.config@2.0 clients, Soong namespace and Makefile packaging/dependency boundary; official AOSP17 graphics owner; modern candidate source-module distinction; absence of a device tree.
- Add immutable, text-only GitHub Actions CI that validates pinned manifest resolver, manifest negative tests, **135-repository matrix**, archive Python tests, AOSP17 official graph and pinned Qualcomm-derived comparison. **No LF52406/LineageOS checkout or proprietary binary input in CI.**
- Companion manifest [Draft PR #2](https://github.com/PixelExperience-Reborn/manifest/pull/2): path/known-alias denial gate in common resolver; two negative tests; stage 193 row. Historical seventeen and default.xml unchanged.

## Release/build gates outside current audit

A complete PE-Reborn platform requires independently pinned AOSP17 sources, manifest resolution and repo sync, Soong bootstrap, host tools and system/product image compilation. If an actual graphics dependency is later needed for the platform, its Soong module definitions/providers, linker dependencies, SELinux, VINTF/FCM and stable AIDL versions must be resolved and compiled against selected AOSP17 revisions. **No fake "compiler success" claims.** Hardware-specific SM8475 device trees and boot validation are explicitly future phases.

**Not performed:** full AOSP17 checkout or build, Qualcomm graphics HAL compilation, device-tree implementation, kernel/module build, firmware, VINTF, graphics CTS/VTS or any physical-device test. Green source CI means only static source and manifest checks succeeded.
