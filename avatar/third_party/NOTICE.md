# Third-party assets and source

- `models/mhr_model.pt`: unmodified official `facebookresearch/MHR` v1.0.1 release, `assets.zip` → `assets/mhr_model.pt`. Apache-2.0; see `MHR_LICENSE.txt`.
- `models/a_pose.npz`, `models/sam_body.npz`, related previews: generated from that MHR release and the team's FitMe control mesh. MHR license retained. These are deployment calibration assets, not outputs from a person's photograph.
- `vendor/sam-3d-body`: official runtime source from commit `b5c765a0d89d789985e186d396315e7590887b94`, copied without modification; see its `LICENSE` (SAM License). Download scripts do not grant or bypass model access.
- Detectron2: installed from official commit `a1ce2f9` during image build. Its detector checkpoint is downloaded from the URL used in the official SAM source.
- MoGe: installed from official commit `925b8ed835a7a9cdb7578ba15c658a0afc969030`. Its model is downloaded from `Ruicheng/moge-2-vitl-normal` at the revision recorded in `download_models.py`.
- `models/fitme_depth_fixed.blend`: original FitMe team asset, included byte-for-byte. Existing asset license/provenance is unchanged. No new ownership/license claim is made here.

SAM photo inference weights, ViTDet weights and MoGe weights are downloaded on the deployment VM; they are not included in this ZIP. Respect each source's license and retain downloaded notices.

## Git distribution (2026-11-11)

The unchanged MHR v1.0.1 model is tracked with Git LFS; the LFS pointer does not change its license. Keep both copies of MHR_LICENSE.txt and this notice in the repository. Release v1.0.1 explicitly added the license to its assets: https://github.com/facebookresearch/MHR/releases/tag/v1.0.1 .

The generated A-pose and binding files are modifications/derived calibration assets, not unchanged official MHR assets. Their provenance is recorded above and in the bundled reports. The original control mesh's external base-mesh/texture redistribution rights cannot be established from the provided package alone; preserve and check those original terms before public redistribution. No new license is granted to that team asset here.

Download-on-VM SAM, ViTDet and MoGe weights and caches remain outside this repository's bundled asset allowlist. This packaging choice is not a claim that the SAM license prohibits all redistribution. The bundled SAM source and its license remain tracked.
