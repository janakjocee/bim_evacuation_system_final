# IFC Corpus Provenance Manifest

Audit date: 16 August 2026; fixture recovery verified 17 August 2026

This manifest records the 16 SHA-256-unique payloads in the 23-path
compatibility run. IFC payloads remain excluded from git because of their size;
this document does not redistribute them. An exact hash match verifies file
identity, while a repository licence records the stated reuse terms. It does
not establish professional suitability or model correctness.

## Verified Sources

The current buildingSMART Sample-Test-Files repository states CC BY 4.0 for its
content. The community archive also states CC BY 4.0 but warns that its files
are community examples, are not official buildingSMART examples and may fail
formal IFC validation.

| Canonical local payload | SHA-256 | Source and licence evidence | Verification |
|---|---|---|---|
| `04_IFC4_buildingSMART_Building_Architecture.ifc` | `3ff9b10bd00c7b96dded51e7ca5a6b69efbea38b049adcdd05fcd247de7e70d5` | [buildingSMART IFC4 PCERT sample](https://github.com/buildingSMART/Sample-Test-Files/tree/main/IFC%204.0.2.1%20%28IFC%204%29/PCERT-Sample-Scene), [CC BY 4.0](https://github.com/buildingSMART/Sample-Test-Files/blob/main/LICENSE) | Exact byte match |
| `05_IFC4_buildingSMART_Building_HVAC.ifc` | `11a8552bc555fa44dfdc49374d1ab2da0a16104c10f086af509f500ce03fa2b3` | Same IFC4 PCERT source and licence | Exact byte match |
| `06_IFC4X3_ADD2_buildingSMART_Building_Architecture.ifc` | `a42962f9e2068040ac96636b1e7f6117150b6c0e3371f81088721b22796e463f` | [buildingSMART IFC4X3 PCERT sample](https://github.com/buildingSMART/Sample-Test-Files/tree/main/IFC%204.3.2.0%20%28IFC4X3_ADD2%29/PCERT-Sample-Scene), [CC BY 4.0](https://github.com/buildingSMART/Sample-Test-Files/blob/main/LICENSE) | Exact byte match |
| `IFC4X3_Building_Structural.ifc` | `0343d5222d38e6be8ac7c31045c692e62c6018c80ea60d2f6023e73b846247ab` | Same IFC4X3 PCERT source and licence | Exact byte match |
| `IFC4_Wall_Opening_Window.ifc` | `73b0e45d931d5dc13bfee5fdc7bd80f796526445458b2de74c4168d209097832` | [buildingSMART Reference View example](https://github.com/buildingSMART/Sample-Test-Files/tree/main/IFC%204.0.2.1%20%28IFC%204%29/ISO%20Spec%20-%20ReferenceView_V1.2), [CC BY 4.0](https://github.com/buildingSMART/Sample-Test-Files/blob/main/LICENSE) | Exact byte match |
| `11134_V_Motebello_Heistopp_Rev.ifc` | `d0dd573388317907e6aa59f86319b5408306f0dbe9feea99cb7b83ed1d62ba3a` | [bimfag/intro-python-bim model](https://github.com/bimfag/intro-python-bim/blob/master/Models/11134_V_Motebello_Heistopp_Rev.ifc), repository declares MIT | Exact byte match |
| `Duplex_A_20110907.ifc` | `b347a2c8aa8fff6db896a4417a9c50c22ac0ccd7c5cfc22b99b8d29336c606ed` | [buildingSMART community Duplex sample](https://github.com/buildingsmart-community/Community-Sample-Test-Files/tree/main/IFC%202.3.0.1%20%28IFC%202x3%29/Duplex%20Apartment), [CC BY 4.0](https://github.com/buildingsmart-community/Community-Sample-Test-Files/blob/main/LICENSE) | Local hash equals the source Git LFS object OID |
| `official_Duplex_Rooms_And_Spaces.ifc` | `3cd577ecff9daf91632789a408070251a431b198de7be47f64e01c7fda1be92b` | [Duplex rooms and spaces source](https://github.com/buildingsmart-community/Community-Sample-Test-Files/blob/main/IFC%202.3.0.1%20%28IFC%202x3%29/Duplex%20Apartment/Duplex_M_20111024_ROOMS_AND_SPACES.ifc), CC BY 4.0 | Exact Git LFS object recovered and hash verified |
| `official_Clinic_Architectural.ifc` | `2ac970ce065ecac4e0c9e5f453a257169e90d0067f419b7e33533a64ef837880` | [buildingSMART community Clinic sample](https://github.com/buildingsmart-community/Community-Sample-Test-Files/tree/main/IFC%202.3.0.1%20%28IFC%202x3%29/Medical-Dental%20Clinic), CC BY 4.0 | Exact Git LFS object recovered and hash verified |

## Historical Source Pointers, Now Resolved Locally

The first local-folder audit found valid Git LFS pointer text rather than IFC
model contents at these paths. Those historical inputs were correctly
classified as failed. The pinned public payloads have since been recovered by
`scripts/recover_public_ifc_fixtures.py`; exact size, SHA-256, trusted HTTPS host
and IFC STEP header checks now pass for all three.

| Historical local pointer | Pointer SHA-256 | Recovered IFC object SHA-256 | Intended source |
|---|---|---|---|
| `01_IFC2X3_Duplex_A_20110907.ifc` | `612251d72fd888e50b5b8aa83a5ba32d41cb8d35663ae92bbdc7ad3cfe8ca8a7` | `b347a2c8aa8fff6db896a4417a9c50c22ac0ccd7c5cfc22b99b8d29336c606ed` | Duplex source above |
| `02_IFC2X3_Duplex_Rooms_And_Spaces.ifc` | `bec9d5c00ff061cb0da77cee2eef657c100d0a670904d3209531bf2c2c584fa7` | `3cd577ecff9daf91632789a408070251a431b198de7be47f64e01c7fda1be92b` | [Duplex rooms and spaces](https://github.com/buildingsmart-community/Community-Sample-Test-Files/blob/main/IFC%202.3.0.1%20%28IFC%202x3%29/Duplex%20Apartment/Duplex_M_20111024_ROOMS_AND_SPACES.ifc) |
| `03_IFC2X3_Clinic_Architectural.ifc` | `e592f013aa0d8903c20bb48c8355f131f96411df3704b93e62a9423a40d21109` | `2ac970ce065ecac4e0c9e5f453a257169e90d0067f419b7e33533a64ef837880` | [buildingSMART community Clinic sample](https://github.com/buildingsmart-community/Community-Sample-Test-Files/tree/main/IFC%202.3.0.1%20%28IFC%202x3%29/Medical-Dental%20Clinic) |

The post-recovery seven-file diagnostic contains zero payload failures and seven
partial engineering results. The remaining partial labels describe missing or
inferred model evidence; they are not download or IFC-opening failures.

## Provenance Not Yet Verified

These files can be used locally to test robustness, but they must not be
described in the report as public or authorised evidence until their original
source and reuse terms are recorded. Header metadata is not a licence.

| Canonical local payload | SHA-256 | Known technical metadata | Required action |
|---|---|---|---|
| `07_IFC4X1_Revit_Dormitory_Spaces.ifc` | `a327f06e34214e43a7a557174ff0a7fdad4156d21f476b3c55ff559a50e5a110` | IFC4X1; IfcPlusPlus export | Record original URL/owner and licence or exclude from reported corpus. |
| `STRUC_NordicLCA_Housing_Concrete_BuildingPermit.ifc` | `586f2d47751bcddb06286072736cdd138bb3de7eebd8513ddc648f5f8a48ab0f` | IFC4; Tekla 2023 structural export | Record original URL/owner and licence or exclude. |
| `STRUC_NordicLCA_Housing_Timber_BuildingPermit.ifc` | `26aad2086dc1b7328f2dfde9f088f35d4db743aef5346a7d8e921e5e2d37904f` | IFC4; Tekla 2023 structural export | Record original URL/owner and licence or exclude. |
| `STRUC_NordicLCA_Office_Concrete_BuildingPermit.ifc` | `c36f33de483c6c0aa9917d281dbbdff0727ca051c586922463277e59fd59801b` | IFC4; Tekla 2023 structural export | Record original URL/owner and licence or exclude. |
| `STRUC_NordicLCA_Office_Timber_BuildingPermit.ifc` | `3beff5c872c55184e0747e5c5faf17bbb5cd6877d8a26a653c4be98a3bf7c25d` | IFC4; Tekla 2023 structural export | Record original URL/owner and licence or exclude. |
| `Clinic_Architectural.ifc` | `4ef2a77d63aecabd7d8d0b77fca268e80a07b1e4bef1ab28f030f2f5b3095c16` | IFC2X3; same name/size class as community Clinic, but hash differs from source LFS OID | Exclude this variant; use the recovered exact `official_Clinic_Architectural.ifc` payload instead. |

The machine-readable subset used by the final research evaluations is recorded
in `evaluation/ifc_corpus_manifest.json`. The unresolved Dormitory and NordicLCA
files are excluded from the claimed licensed evaluation corpus until provenance
is supplied.

## Hugging Face Provenance-Pending Stress Corpus

The following seven local files were described by the project author as
downloaded from Hugging Face. The exact dataset URL, revision and licence were
not available during this audit. They were therefore used only for local parser
and robustness testing and are excluded from the claimed licensed evaluation
corpus.

| Local file | SHA-256 | Bytes | Schema | Final diagnostic |
|---|---|---:|---|---|
| `arc.ifc` | `e91ddbbd672bbde946af14631de4c732f0cf8a7cfae5dbbf06fbeab03b5c46df` | 342657851 | IFC2X3 | Partial |
| `ventilation.ifc` | `c78f6ad085961500f0890bbffda9e171c1342c5865ca152f64098dd4da644cca` | 114891068 | IFC2X3 | Partial |
| `electrical.ifc` | `adb8d5eda2c706a1fded2a00bd38d845e35f513e2f6ba048fc6228274dfb3986` | 97058912 | IFC2X3 | Partial |
| `arc_ifc2x3.ifc` | `989ace1d52f694ee94d80bd99aa81d0ff3d76cf21f34fcfd00a286ac897ed8a6` | 80318141 | IFC2X3 | Partial |
| `arc (2).ifc` | `fe8da4917769c23227468e3be0af6f7f05d53dd8da23c275e2f256343df42f32` | 73945142 | IFC2X3 | Partial |
| `arc (1).ifc` | `57fafa59f03b18c05be211a456e346bdd0445d5c35d66522e598d339e81dfcf4` | 65078748 | IFC2X3 | Partial |
| `kitchen.ifc` | `1905b992071729d1c780b18f6103e4d1d08307a4707d5f33a4413216f36776ac` | 49670229 | IFC2X3 | Partial |

The before/after run changed `arc.ifc` from fail to partial after IFC unit
normalisation and inferred-topology recovery. Across all seven payloads,
disconnected spaces reduced from 131 to 75 and spaces without an exit route
reduced from 131 to 110. No payload achieved strict pass because no tested route
had enough verified edge evidence. Local reproducible evidence is written to:

```text
outputs/huggingface_ifc_diagnostics_20260816/
outputs/huggingface_ifc_diagnostics_after_20260816/
outputs/huggingface_ifc_comparison_20260816/
```

Required before report inclusion: record the Hugging Face dataset URL, immutable
revision, dataset-card licence, attribution instructions and each model's source
family. A platform name alone is not provenance.

## Duplicate Accounting

The remaining seven tested paths are renamed copies of five verified payloads:
IFC4 Architecture occurs twice, IFC4 HVAC three times, IFC4X3 Architecture
three times, IFC4X3 Structural twice, and the wall/opening payload twice. The
batch diagnostic records `duplicate_payload_of` and
`payload_occurrence_count`; duplicates must not be presented as independent
validation models.
