# Versões

Atualizar este arquivo na branch `main` dispara o build e o push das imagens
`emersonbottega/backend` e `emersonbottega/frontend` para o Docker Hub
(workflow `.github/workflows/docker-publish.yml`).

A versão publicada é a do **primeiro** título `## <versão>` abaixo (formato
`MAJOR.MINOR.PATCH`). As imagens recebem a tag da versão e a tag `latest`.
Adicione as novas versões no topo.

## 1.1.1 - 2026-10-23

- Republicação das imagens para testar a atualização automática via Watchtower.

## 1.1.0 - 2026-10-23

- Frontend repassa as chamadas `/api` ao backend pela rede interna do Docker
  (`API_PROXY_TARGET`); a API deixa de ser exposta no `compose.dockerhub.yml`.
- `compose.dockerhub.yml` publica o frontend na porta 3100.

## 1.0.0 - 2026-10-22

- Primeira versão publicada no Docker Hub.
hello
