# Backstage local template

`catalog-info.yaml` declares an experimental control-plane component with a platform owner. `template.yaml` collects sandbox deployment request fields using Backstage's scaffolder schema and logs them with `debug:log` only. No Backstage instance is connected, the template is not registered, and it does not call the control-plane API. The API's `GET /workflows/{id}` and `GET /workflows/{id}/report` are the current local status contract; a production status view must add authenticated tenant scoping before rendering it in Backstage.

The newer `apps/developer-portal/` package adds a typed Backstage frontend request view. It does not replace this catalog/template example or provide an authenticated host backend.
