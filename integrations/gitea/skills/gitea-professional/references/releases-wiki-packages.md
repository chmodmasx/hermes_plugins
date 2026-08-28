# Releases, Wiki, and Packages

## Releases

Repository release APIs include list/get/latest/by-tag/create/edit/delete and asset operations. Discover exact asset upload/download/delete paths from the live schema because payload/content handling differs from simple JSON operations.

Rules:

- distinguish Git tag creation from release creation;
- verify the tag and target commit before publishing a release;
- do not silently retag an existing release;
- use draft/prerelease intentionally;
- deleting a release is destructive and does not necessarily imply deleting the Git tag unless an endpoint/option explicitly does so.

Helper commands:

- `release list OWNER REPO`
- `release create OWNER REPO --tag TAG [--name ... --body ... --target ... --draft --prerelease]`
- `release delete OWNER REPO ID --confirm DELETE_RELEASE:OWNER/REPO:ID`

## Wiki

Current wiki endpoints include:

- `GET /repos/{owner}/{repo}/wiki/pages`
- `GET /repos/{owner}/{repo}/wiki/page/{pageName}`
- `POST /repos/{owner}/{repo}/wiki/new`
- `PATCH /repos/{owner}/{repo}/wiki/page/{pageName}`
- `DELETE /repos/{owner}/{repo}/wiki/page/{pageName}`

Create/edit payloads use base64-encoded content plus title/message fields. The helper reads a local file and base64-encodes it, avoiding model-generated manual base64.

Before editing a wiki page, fetch it first. Before deletion, exact confirmation is required.

## Packages

The package API can list packages and versions, get latest/version/files, delete package/version, and link/unlink packages to repositories.

Common current paths:

- `GET /packages/{owner}`
- `GET /packages/{owner}/{type}/{name}`
- `GET /packages/{owner}/{type}/{name}/-/latest`

Package types documented by current Gitea include ecosystems such as Alpine, Cargo, Chef, Composer, Conan, Conda, Container, CRAN, Debian, Generic, Go, Helm, Maven, npm, NuGet, Pub, PyPI, RPM, RubyGems, Swift, Terraform, Vagrant, and others as the server evolves.

Use the live schema for delete/link/unlink details. Package deletion is destructive and may affect downstream deployments; require explicit authorization and verify remaining versions afterward.

## Source links

- https://docs.gitea.com/api/operations/repo-list-releases/
- https://docs.gitea.com/api/operations/repo-get-latest-release/
- https://docs.gitea.com/api/operations/repo-get-wiki-pages/
- https://docs.gitea.com/api/operations/repo-get-wiki-page/
- https://docs.gitea.com/api/operations/repo-create-wiki-page/
- https://docs.gitea.com/api/operations/repo-edit-wiki-page/
- https://docs.gitea.com/api/operations/repo-delete-wiki-page/
- https://docs.gitea.com/api/operations/list-packages/
