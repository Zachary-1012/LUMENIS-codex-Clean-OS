# Facebook Metrics public CSV fixture

Moro, S., Rita, P., & Vala, B. (2016). Facebook Metrics [Dataset]. UCI Machine Learning Repository. DOI: https://doi.org/10.24432/C5QK55

- Publisher page: https://archive.ics.uci.edu/dataset/368/facebook+metrics
- Official original download: https://archive.ics.uci.edu/static/public/368/facebook+metrics.zip
- License: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/ . UCI lists this license on the publisher page.
- Retrieved and independently matched: 2026-10-21 11:27 UTC (19:27 Beijing, UTC+08:00).
- Original ZIP SHA256: 48e4739b4acbbcca8f03cbcfe145d82c2e665cdd5bb9e20618690d454ce93fd3.
- Member: dataset_Facebook.csv, 37,891 bytes, SHA256 666ec82952b7ce90b464f5a87ec4f0fe92d9a63208f2fcb2d0443cb5f31c3f4c.
- Changes: none. The original member bytes, semicolon delimiter, line endings and missing cells are preserved. No semantic version or HTTP Last-Modified/ETag was supplied; the hash fixes this snapshot.

This is the authors' publicly released 500-post subset of 790 historical posts from an anonymized cosmetics brand's Facebook page in 2014. It contains aggregate post metrics, not private user account exports. The excluded rows/material are not recovered or inferred. The CSV has 19 columns and six missing cells despite the catalog's no-missing metadata.

The fixture tests CSV parsing, missing-cell preservation and original-byte identity only. It does not prove current Facebook collection, production data, model quality or complete product acceptance. Tests never download this resource. An explicit LUMENIS_REAL_FACEBOOK_CSV override remains supported but must match the same exact SHA256; missing or altered input fails rather than being silently substituted.
