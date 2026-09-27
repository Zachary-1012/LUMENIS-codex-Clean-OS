{{flutter_js}}
{{flutter_build_config}}

// The workspace uses current online assets; Flutter owns legacy worker cleanup.
// Keep the renderer on the Workspace host, including deep-linked routes.
_flutter.loader.load({
  config: {
    canvasKitBaseUrl: new URL('canvaskit/', document.baseURI).href,
  },
});
