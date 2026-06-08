# Practical Feature Benchmark

This project was reviewed against open-source BIM viewing/analysis tools and
current UK means-of-escape guidance. The review informs the practical features
implemented in the Streamlit prototype without claiming certified analysis.

## Implemented in this prototype

- Interactive top-down IFC footprints and rotatable 3D screening views.
- Visible exits/egress markers and highlighted evacuation-route inspection.
- Alternative-exit awareness and travel-distance screening.
- Scenario evidence export, operational action checklist and explicit model-quality limitations.
- Accessibility/refuge and emergency-lighting/signage prompts for expert confirmation.

## Evidence considered

- [IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell) provides IFC parsing
  and geometry support across major IFC schema families.
- [opensourceBIM voxelization toolkit](https://github.com/opensourceBIM/voxelization_toolkit)
  demonstrates obstacle-aware evacuation-distance analysis using voxelized IFC geometry.
- [BIMsurfer](https://github.com/opensourceBIM/BIMsurfer) demonstrates high-performance
  WebGL IFC viewing, measurement and section-plane interaction.
- [BIMROCKET](https://github.com/bimrocket/bimrocket) demonstrates model selection,
  property inspection, measurement and reporting workflows.
- [Approved Document B Volume 2](https://www.gov.uk/government/publications/fire-safety-approved-document-b)
  emphasizes travel distance, alternative escape routes, exit positioning and protected escape.
- [UK means of escape for disabled people research](https://www.gov.uk/government/publications/fire-safety-means-of-escape-for-disabled-people/fire-safety-means-of-escape-for-disabled-people-executive-summary)
  highlights refuge, assisted escape and inclusive-design considerations.

## Recommended future engineering work

- Voxel or navigation-mesh routing that accounts for walls, obstacles and headroom.
- True IFC mesh streaming through glTF/WebGL with object selection and section planes.
- BCF issue exchange and IDS-based model-information requirements.
- Calibrated crowd simulation and professional fire-dynamics validation.
