# DESIGN_ONLY fixtures (not production data)
- fixtures.js : 5 demo subjects (prototype only)
- screens.viewmodel.js : copy of the 44-screen viewmodel with DESIGN_ONLY content
Every screen root is marked data-source=prototype at mount. Replace via REPLACEMENT_LIST.json (54 bindings). Do not edit these to "look real" — they are explicit placeholders.
