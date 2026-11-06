# Dataset

## Source

**RealWaste** — Single, Iranmanesh & Raad, *Information* 2023, 14(12), 633.
DOI: 10.3390/info14120633 (also on IEEE DataPort, DOI 10.21227/65m5-rr72, and UCI).
Licence: **CC BY-NC-SA 4.0**. 4,752 images, 524×524, photographed at Whyte's
Gully, Wollongong, Australia.

Kaggle: https://www.kaggle.com/datasets/joebeachcapital/realwaste

The dataset images themselves are **not** included in this repo. Download
RealWaste from the link above and apply the remap below.

## 9-class → 4-class remap

| Our class | RealWaste classes merged in |
|---|---|
| Paper | Paper (500) |
| Plastic | Plastic (921) |
| Food | Food Organics (411) |
| Others | Cardboard (461), Glass (420), Metal (790), Miscellaneous Trash (495), Textile Trash (318), Vegetation (436) |

Local phone photos (~71 per class, ~284 total) were added on top.

## Counts as measured in our folders

| Class | Images |
|---|---|
| Paper | 1,831 |
| Plastic | 1,674 |
| Food | 1,461 |
| Others | 1,885 |
| **Total** | **6,851** |

Split used for training: stratified 70/15/15 (seed 42) — train 4,793 / val 1,026 /
test 1,032. See `training/yolov8-smart-bin-retrain-colab.ipynb`.

## Provenance note (honest, in progress)

A plain remap of RealWaste (4,752) plus ~284 phone photos accounts for 5,036
images, so **1,815 images in our folders are not yet explained** by those two
sources (possible augmentation / duplicates / an additional source — not yet
confirmed). `training/provenance-audit-colab.ipynb` checks for exact duplicates
(MD5), near-duplicates (perceptual hash) and train/val/test leakage; run it on
`realwaste1.zip` and see the audit output before citing the counts. The paper
states this gap openly in its Limitations section.

## Attribution

If you use this dataset, cite:

> Single, A., Iranmanesh, S., & Raad, A. (2023). RealWaste: A Novel Real-Life
> Dataset for Landfill Waste Classification. *Information*, 14(12), 633.
> https://doi.org/10.3390/info14120633
