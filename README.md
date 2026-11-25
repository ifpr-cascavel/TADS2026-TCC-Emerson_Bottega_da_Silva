# Geração de malhas computacionais com Triangulação de Delaunay e Diagramas de Voronoi

Protótipo do TCC que gera **malhas computacionais bidimensionais** a partir de uma
área geolocalizada delimitada pelo usuário, utilizando **triangulação de Delaunay**
e **diagramas de Voronoi** para apoiar a análise espacial de pontos de monitoramento.

O projeto é composto por:

- uma **API REST** (Python/Flask) responsável por receber coordenadas geográficas,
  gerar as estruturas geométricas e disponibilizar os dados (inclusive em GeoJSON);
- um **protótipo web** (React) que permite delimitar a área sobre um mapa
  interativo (OpenStreetMap/Leaflet), gerar e visualizar a malha e exportar o
  resultado.

A malha é construída por **Triangulação de Delaunay Restrita** (CDT), o que garante
que os triângulos sejam gerados **exclusivamente dentro** do polígono delimitado. A
partir dela o sistema também sugere **pontos candidatos a sensores** e permite
**particionar** a malha em regiões balanceadas.

---

## Sumário

- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Como executar](#como-executar)
- [Deploy no Render](#deploy-no-render)
- [API REST](#api-rest)
  - [Formato padrão de resposta](#formato-padrão-de-resposta)
  - [`GET /api/v1/status`](#get-apiv1status)
  - [`POST /api/v1/meshes`](#post-apiv1meshes)
  - [`POST /api/v1/meshes/partitions`](#post-apiv1meshespartitions)
  - [`POST /api/v1/meshes/geojson`](#post-apiv1meshesgeojson)
  - [Códigos de erro](#códigos-de-erro)
- [Uso do protótipo](#uso-do-protótipo)
- [Licença](#licença)

---

## Arquitetura

A API segue o padrão **REST** e adota uma **separação clara de responsabilidades**
em camadas (Controllers, Services, Models, Validação, Erros e Respostas), aplicando
princípios de Clean Code e SOLID.

```
prototype/
├── backend/                                # API REST (Flask)
│   ├── app.py                              # Ponto de entrada; expõe `application`
│   ├── requirements.txt
│   ├── Dockerfile
│   └── mesh_api/                           # Pacote da aplicação
│       ├── __init__.py                     # Fábrica da aplicação (create_application)
│       ├── controllers/                    # Camada de rotas (REST)
│       │   ├── mesh_controller.py
│       │   └── status_controller.py
│       ├── services/                       # Regras de negócio
│       │   ├── mesh_generation_service.py       # CDT (Delaunay restrita) + Voronoi
│       │   ├── mesh_partitioning_service.py     # Particionamento (METIS + fallback)
│       │   ├── sensor_placement_service.py      # Candidatos a sensores
│       │   ├── geojson_export_service.py        # Exportação GeoJSON
│       │   └── geometry.py                       # Utilitários geométricos reutilizáveis
│       ├── models/                         # Objetos de domínio
│       │   ├── geographic_point.py
│       │   ├── mesh_generation_request.py
│       │   └── mesh_generation_result.py
│       ├── validation/                     # Validação das entradas
│       │   └── mesh_generation_request_validator.py
│       ├── errors/                         # Exceções e tratamento global
│       │   ├── api_exceptions.py
│       │   └── error_handlers.py
│       └── responses/                      # Envelope padronizado
│           └── standardized_api_response.py
│
└── frontend/                               # Protótipo (React + Leaflet)
    └── src/
        ├── App.js                          # Estado da aplicação e orquestração
        ├── App.css                         # Design tokens e estilos
        ├── components/                     # Componentes de interface
        │   ├── MapView.js                  # Mapa (Leaflet/OpenStreetMap) e camadas
        │   ├── ControlPanel.js             # Painel de parâmetros e ações
        │   ├── PartitionCountField.js      # Campo validado de nº de partições
        │   ├── MapLegend.js                # Legenda dos elementos do mapa
        │   └── StatusBanner.js             # Mensagens de erro/sucesso
        ├── services/
        │   └── meshService.js              # Cliente HTTP da API
        └── config/
            ├── mapVisuals.js               # Cores/estilos (fonte única de verdade)
            └── meshParameters.js           # Limites numéricos dos parâmetros
```

**Fluxo de uma requisição de geração de malha:**

1. O **controlador** recebe a requisição HTTP e delega a validação.
2. O **validador** verifica a entrada e a converte em um objeto de domínio
   (`MeshGenerationRequest`), acumulando todas as mensagens de erro.
3. O **serviço de geração** produz a Triangulação de Delaunay Restrita ao polígono
   (com refinamento opcional), o diagrama de Voronoi, os candidatos a sensores e,
   quando solicitado, o particionamento — retornando um `MeshGenerationResult`.
4. O resultado é serializado no **envelope padronizado** e devolvido ao cliente.
5. Qualquer exceção é capturada pelo **tratamento global de erros**, garantindo uma
   resposta consistente e o código HTTP correto — sem `try/except` nos controladores.

---

## Tecnologias

| Camada        | Tecnologia                                                       |
|---------------|------------------------------------------------------------------|
| Backend       | Python 3.12, Flask, Flask-CORS, NumPy, SciPy                     |
| Triangulação  | Triangle (Constrained Delaunay Triangulation)                    |
| Particionamento | PyMETIS (METIS) com fallback em Python puro (RCB)              |
| Frontend      | React 19, react-leaflet, Leaflet, Axios                          |
| Mapa          | OpenStreetMap (gratuito, sem chave de API)                       |
| Exportação    | GeoJSON (`application/geo+json`)                                  |

---

## Como executar

### Pré-requisitos

- **Python 3.12+**
- **Node.js 18+** e **npm**

### 1. Backend (API Flask)

A partir da pasta `prototype/backend`:

```bash
py -3.12 -m venv venv
```

Ative o ambiente virtual:

- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Linux/macOS:**
  ```bash
  source venv/bin/activate
  ```

Instale as dependências e inicie a API:

```bash
pip install -r requirements.txt
```

```bash
python app.py
```

A API ficará disponível em **http://localhost:5000**.

> **Importante (Windows):** o comando `python app.py` só funciona com o ambiente
> virtual **ativado** — caso contrário, o `python` global (que não tem o Flask
> instalado) será usado e ocorrerá `ModuleNotFoundError: No module named 'flask'`.
> Se a ativação for bloqueada pela política de execução do PowerShell, chame o
> Python do venv diretamente, sem ativar:
>
> ```powershell
> .\venv\Scripts\python.exe app.py
> ```

Verifique com: `curl http://localhost:5000/api/v1/status`

### 2. Frontend (protótipo React)

A partir da pasta `prototype/frontend`:

```bash
npm install
```

```bash
npm start
```

O protótipo ficará disponível em **http://localhost:3000** e consumirá a API em
`http://localhost:5000`.

### 3. Executar com Docker (opcional)

A partir da raiz do repositório:

```bash
docker compose up --build
```

Isso constrói e sobe o **backend** (porta 5000) e o **frontend** (porta 3000), conforme o `compose.yml`.

## Deploy no Render

O arquivo `render.yaml` configura os dois serviços no plano gratuito do Render:

- `tcc-delaunay-backend`: Web Service Docker para a API Flask;
- `tcc-delaunay-frontend`: Static Site para o build React.

No Render, crie um Blueprint apontando para este repositório e selecione o arquivo
`render.yaml`. Após o primeiro deploy do backend, copie a URL pública dele e informe
esse valor como `REACT_APP_API_BASE_URL` nas variáveis do serviço frontend:

```text
REACT_APP_API_BASE_URL=https://tcc-delaunay-backend.onrender.com
```

Depois, faça um novo deploy do frontend para incorporar a URL ao build. O endpoint
de saúde da API é `/api/v1/status`. No plano gratuito, o backend pode entrar em
suspensão após um período sem requisições e levar aproximadamente um minuto para
responder ao primeiro acesso seguinte.

### CI/CD

O workflow `.github/workflows/ci.yml` (GitHub Actions) roda em todo push para `main`
e em pull requests:

- **Backend**: instala as dependências e executa os testes (`pytest`) em
  `prototype/backend/tests`;
- **Frontend**: executa os testes (`npm test`) e o build de produção (`npm run build`,
  com `CI=true`, que trata avisos do ESLint como erros);
- **Docker**: constrói as imagens do backend e do frontend e faz um smoke test do
  backend em `/api/v1/status`.

O deploy contínuo é feito pelo próprio Render: em `render.yaml`, os serviços usam
`autoDeployTrigger: checksPass`, ou seja, um commit em `main` só é publicado depois
que todos os checks do GitHub passarem.

#### Imagens no Docker Hub

O workflow `.github/workflows/docker-publish.yml` constrói e publica as imagens
`emersonbottega/backend` e `emersonbottega/frontend` (linux/amd64 e linux/arm64)
sempre que o arquivo `versions.md` é alterado na `main`. A tag publicada é a do
primeiro título `## MAJOR.MINOR.PATCH` desse arquivo, além de `latest`. O login no
Docker Hub usa o usuário `emersonbottega` e o secret `DOCKERHUB_TOKEN` do repositório.

Para subir o projeto a partir dessas imagens, sem build local:

```bash
docker compose -f compose.dockerhub.yml up -d
# ou, fixando uma versão:
IMAGE_TAG=1.0.0 docker compose -f compose.dockerhub.yml up -d
```

Para rodar os testes do backend localmente:

```bash
cd prototype/backend
pip install -r requirements.txt pytest
python -m pytest
```

### Proteções da API em produção

As operações de geração de malha possuem limite de **5 requisições por minuto por IP**. O endpoint de saúde não é limitado. Quando o limite é excedido, a API retorna
HTTP `429` com o erro padronizado `RATE_LIMIT_EXCEEDED`.

O backend usa `ProxyFix` para identificar o IP encaminhado pelo proxy do Render e restringe o CORS ao frontend local e ao domínio configurado em
`CORS_ALLOWED_ORIGINS`. O armazenamento padrão do rate limiting é em memória, adequado ao serviço gratuito de uma única instância;

---

## API REST

Base URL: `http://localhost:5000`

Todos os endpoints de dados aceitam e retornam **JSON** (exceto o download GeoJSON,
que retorna `application/geo+json`).

### Formato padrão de resposta

Toda resposta JSON segue o mesmo envelope, facilitando o consumo pelo protótipo e
por clientes externos:

**Sucesso**
```json
{
  "success": true,
  "data": { "...": "..." },
  "error": null
}
```

**Erro**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request could not be processed: it contains invalid data.",
    "details": ["The 'boundaryPoints' field is required."]
  }
}
```

---

### `GET /api/v1/status`

Verificação de disponibilidade da API (health check). Informa também se o METIS está
disponível no ambiente atual.

**Exemplo (cURL)**
```bash
curl http://localhost:5000/api/v1/status
```

**Resposta — 200 OK**
```json
{
  "success": true,
  "data": { "status": "operational", "metisAvailable": true },
  "error": null
}
```

---

### `POST /api/v1/meshes`

Gera a Triangulação de Delaunay Restrita e o diagrama de Voronoi para os pontos
informados. Aceita, opcionalmente, `partitionCount` para também particionar a malha.

**Corpo da requisição**

| Campo             | Tipo             | Obrigatório | Descrição                                                                       |
|-------------------|------------------|-------------|---------------------------------------------------------------------------------|
| `boundaryPoints`  | lista de objetos | Sim         | Pontos que delimitam a área. Mínimo de **3**.                                   |
| `boundaryPoints[].lat` | número      | Sim         | Latitude em graus decimais, entre **-90** e **90**.                             |
| `boundaryPoints[].lng` | número      | Sim         | Longitude em graus decimais, entre **-180** e **180**.                          |
| `maxEdgeLength`   | número (> 0)     | Não         | Comprimento máximo de aresta (em graus) para refinamento. Vazio = sem refino.   |
| `partitionCount`  | inteiro ≥ 1      | Não         | Número de partições da malha (1 = não particionar). Máximo: **32**. Padrão: 1.  |

> **Refinamento:** quando `maxEdgeLength` é informado, o comprimento é convertido em
> uma área máxima de triângulo e a triangulação insere pontos internos (pontos de
> Steiner) até respeitar esse limite. Valores menores geram malhas mais densas.

**Validações**
- corpo deve ser um objeto JSON;
- `boundaryPoints` obrigatório, do tipo lista, com pelo menos 3 elementos;
- cada ponto deve ter `lat`/`lng` numéricos dentro dos intervalos válidos;
- `maxEdgeLength`, se presente, deve ser numérico e maior que zero;
- `partitionCount`, se presente, deve ser inteiro entre 1 e 32.

**Dados retornados (`data`)**

| Campo                | Descrição                                                                                  |
|----------------------|--------------------------------------------------------------------------------------------|
| `originalPoints`     | Pontos informados pelo usuário (`{lat, lng}`).                                              |
| `meshPoints`         | Pontos efetivamente usados na malha, incluindo os inseridos pelo refinamento.              |
| `triangles`          | Lista de triângulos; cada um é uma tripla de índices que apontam para `meshPoints`.        |
| `voronoiVertices`    | Vértices do diagrama de Voronoi (`{lat, lng}`).                                             |
| `voronoiEdges`       | Arestas **finitas** do diagrama de Voronoi (`{start, end}`).                                |
| `sensorCandidates`   | Pontos candidatos a sensores (circuncentros dos triângulos dentro do polígono).            |
| `trianglePartitions` | Id da partição de cada triângulo, alinhado por índice a `triangles`. Vazio se não houver.  |
| `partitionCount`     | Número de partições efetivamente produzidas.                                               |

**Exemplo (cURL)**
```bash
curl -X POST http://localhost:5000/api/v1/meshes \
  -H "Content-Type: application/json" \
  -d '{
    "boundaryPoints": [
      {"lat": -24.95, "lng": -53.46},
      {"lat": -24.95, "lng": -53.44},
      {"lat": -24.93, "lng": -53.45},
      {"lat": -24.92, "lng": -53.47},
      {"lat": -24.94, "lng": -53.48}
    ],
    "maxEdgeLength": 0.01,
    "partitionCount": 3
  }'
```

**Resposta — 200 OK** (resumida)
```json
{
  "success": true,
  "data": {
    "originalPoints": [{"lat": -24.95, "lng": -53.46}, "..."],
    "meshPoints": [{"lat": -24.95, "lng": -53.46}, "..."],
    "triangles": [[2, 0, 1], [0, 2, 3], [0, 3, 4]],
    "voronoiVertices": [{"lat": -24.9425, "lng": -53.45}],
    "voronoiEdges": [
      {"start": {"lat": -24.9425, "lng": -53.45}, "end": {"lat": -24.935, "lng": -53.465}}
    ],
    "sensorCandidates": [{"lat": -24.9401, "lng": -53.4562}],
    "trianglePartitions": [0, 1, 2],
    "partitionCount": 3
  },
  "error": null
}
```

**Exemplo de erro — 400 Bad Request**
```bash
curl -X POST http://localhost:5000/api/v1/meshes \
  -H "Content-Type: application/json" \
  -d '{"boundaryPoints": [{"lat": -24.95, "lng": -53.46}, {"lat": -24.95, "lng": -53.44}]}'
```
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request could not be processed: it contains invalid data.",
    "details": ["At least 3 points are required to generate the mesh; 2 were received."]
  }
}
```

---

### `POST /api/v1/meshes/partitions`

Endpoint dedicado ao **particionamento**: gera a malha e a divide em partições
balanceadas por meio do particionamento do grafo dual (METIS, com fallback em Python
puro). O corpo é **idêntico** ao de `POST /api/v1/meshes`; a diferença é que, aqui,
`partitionCount` assume **2** quando omitido (o propósito do endpoint é particionar).

O resultado tem o mesmo formato de `POST /api/v1/meshes`, com `trianglePartitions` e
`partitionCount` preenchidos.

**Exemplo (cURL)**
```bash
curl -X POST http://localhost:5000/api/v1/meshes/partitions \
  -H "Content-Type: application/json" \
  -d '{
    "boundaryPoints": [
      {"lat": -24.95, "lng": -53.46},
      {"lat": -24.95, "lng": -53.44},
      {"lat": -24.93, "lng": -53.45},
      {"lat": -24.92, "lng": -53.47},
      {"lat": -24.94, "lng": -53.48}
    ],
    "maxEdgeLength": 0.008,
    "partitionCount": 4
  }'
```

---

### `POST /api/v1/meshes/geojson`

Gera a malha e a devolve como um **arquivo GeoJSON** para download, no formato padrão
consumido por ferramentas de geoprocessamento (ex.: QGIS). O corpo da requisição é
**idêntico** ao de `POST /api/v1/meshes`.

A resposta é uma `FeatureCollection` cujas feições possuem a propriedade `type`:
`original_point`, `mesh_point`, `sensor_candidate`, `triangle` e `voronoi_edge`. Quando
a malha é particionada, cada feição `triangle` também traz a propriedade `partition`.

- `Content-Type: application/geo+json`
- `Content-Disposition: attachment; filename="mesh.geojson"`

**Exemplo (cURL) — salvando o arquivo**
```bash
curl -X POST http://localhost:5000/api/v1/meshes/geojson \
  -H "Content-Type: application/json" \
  -d '{
    "boundaryPoints": [
      {"lat": -24.95, "lng": -53.46},
      {"lat": -24.95, "lng": -53.44},
      {"lat": -24.93, "lng": -53.45},
      {"lat": -24.92, "lng": -53.47},
      {"lat": -24.94, "lng": -53.48}
    ]
  }' \
  -o mesh.geojson
```

---

### Códigos de erro

| HTTP | `code`                | Quando ocorre                                                             |
|------|-----------------------|---------------------------------------------------------------------------|
| 400  | `INVALID_INPUT`       | Corpo ou campos inválidos (ver `details`).                               |
| 404  | `RESOURCE_NOT_FOUND`  | Rota inexistente.                                                        |
| 405  | `METHOD_NOT_ALLOWED`  | Método HTTP não suportado pela rota.                                     |
| 422  | `INVALID_GEOMETRY`    | Pontos válidos, mas colineares/coincidentes (não formam uma área).      |
| 500  | `INTERNAL_ERROR`      | Falha inesperada no servidor.                                           |

---

## Uso do protótipo

1. Abra **http://localhost:3000** com a API em execução.
2. **Clique no mapa** para adicionar os pontos que delimitam a área (mínimo de 3).
3. (Opcional) Informe o **número de partições** e/ou o **refinamento** (comprimento
   máximo de aresta). Os campos validam a entrada e sinalizam valores inválidos.
4. Clique em **Gerar malha** para exibir:
   - a **triangulação de Delaunay**, restrita ao polígono;
   - o **diagrama de Voronoi** (linhas verdes tracejadas);
   - os **pontos candidatos a sensores** (em cor âmbar);
   - as **partições** (triângulos coloridos por partição), quando `partições > 1`.
5. Consulte a **legenda** (canto inferior direito do mapa) para o significado de cada
   elemento.
6. Clique em **Baixar GeoJSON** para exportar o resultado.
7. Use **Limpar** para recomeçar a delimitação.

---

## Licença

Este projeto é distribuído sob a **Licença MIT**. Consulte o arquivo
[`LICENSE`](./LICENSE) para o texto completo.
