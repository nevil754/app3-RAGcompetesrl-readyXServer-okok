
questo prj batterà app RAG internazionalmente famose come Legora/Harvey/ LexRoom (italiana)

//in futuro fovrai pensare anche al GDPR per la privacy, quindi anonimizzare i dati sensibili!
//⚠️⚠️ TODO FUTURE/ATTENTIONS!!!
-manca tabella tsql 'conversation_summaries' chiamata in conversation_repo.py & long_term.py !!
-TODO: 
--check se readbeat (x celry cosi che salva i tasks periodici in modo persistente su redis)
--agents con flow Supervisore , ... ect..
--files dentro mcp/
--user_facts tab on sqlserver che appare in files long_term.py non c'è in init.sql, 
--metadata_config_file e path fallback "/app/config/metadata.yaml" in file metadata.py


############################################################################

# RAG Enterprise Legal — Struttura Progetto Completa

```
rag-enterprise/
│
├── main.py                          # Entry point FastAPI — app factory, lifespan, router include
│
├── docker-compose.yml               # Stack produzione completo
├── docker-compose.override.yml      # Override sviluppo locale (hot reload, meno RAM, no password)
│
├── .env                             # Segreti reali (NON committato — nel .gitignore)
├── .env.example                     # Template variabili d'ambiente (committato)
├── .gitignore
├── .dockerignore
│
├── requirements.txt                 # Lock file generato da pip-compile (dipendenze + transitive)
├── requirements-dev.txt             # Lock file dev (test, linting)
├── pyproject.toml                   # Config Ruff, Mypy, Pytest
├── README.md                        
│
├── config/                          # Configurazione centralizzata — committata, no segreti
│   ├── config.yaml                  # ★ Parametri app: LLM, embeddings, retriever, chunking, ecc.
│   ├── prompts.yaml                 # Tutti i prompt LLM centralizzati qui
│   ├── metadata.yaml                # Mapping metadati documenti per classificazione automatica
│   └── logging.yaml                 # Configurazione Loguru
│
│
├── docker/                          # Dockerfile e script infrastruttura
│   ├── fastapi.Dockerfile           # Multi-stage build: builder + runtime leggero
│   ├── celery.Dockerfile            # Separato da FastAPI: pre-scarica modelli embedding
│   └── sqlserver/
│       ├── init.sql                 # ★ Script SQL eseguito al primo avvio del container
│       └── entrypoint.sh            # Attende SQL Server pronto poi esegue init.sql
│
│
├── app/
│   │
│   ├── core/                        # Infrastruttura condivisa — singleton, caricati una volta
│   │   ├── settings.py              # ★ Pydantic-settings: merge config.yaml + .env + OS vars
│   │   ├── observability.py         # Setup Loguru, LangSmith, OpenTelemetry
│   │   ├── security.py              # JWT encode/decode, bcrypt, API key generation
│   │   ├── llm_factory.py           # Factory LLM: ollama | openai | google da config
│   │   ├── embeddings.py            # fastembed BAAI/BGE-M3 wrapper + reranker cross-encoder
│   │   ├── vectorstore.py           # Qdrant client + gestione collection per tenant
│   │   └── redis_client.py          # TenantRedis: namespace isolation tenant:{id}:*
│   │
│   ├── api/
│   │   ├── deps.py                  # ★ Depends FastAPI: CurrentTenant, CurrentDB, CurrentRedis
│   │   │
│   │   ├── middleware/
│   │   │   ├── tenant.py            # Estrae tenant_id dal JWT → request.state
│   │   │   ├── logging.py           # Structured logging con request_id per ogni request
│   │   │   └── rate_limit.py        # Rate limiting per tenant via Redis (fail open)
│   │   │
│   │   └── routes/
│   │       ├── health.py            # GET /health (liveness) e /ready (readiness + checks)
│   │       ├── auth.py              # POST /login, /refresh, /logout · GET /me
│   │       ├── chat.py              # POST /chat/query (sync) e /chat/stream (SSE)
│   │       ├── documents.py         # POST /upload · GET /documents · DELETE /{id}
│   │       ├── collections.py       # CRUD collection (cartelle logiche documenti)
│   │       ├── jobs.py              # GET /jobs, /{id} · POST /{id}/cancel
│   │       ├── users.py             # CRUD utenti (solo admin)
│   │       └── tenants.py           # Provisioning tenant (solo superadmin)
│   │
│   ├── db/
│   │   ├── sqlserver.py             # ★ TenantDB: engine + schema switching per tenant
│   │   │
│   │   ├── models/
│   │   │   └── shared.py            # SQLAlchemy models schema shared (Tenant, AuditLog, ecc.)
│   │   │
│   │   └── repositories/            # Pattern repository: tutta la logica SQL qui
│   │       ├── base.py              # BaseRepository con execute/fetchone/fetchall/scalar
│   │       ├── document_repo.py     # DocumentRepository + IngestionJobRepository
│   │       ├── conversation_repo.py # ConversationRepository + summary long-term memory
│   │       └── user_repo.py         # UserRepository CRUD
│   │
│   ├── rag/
│   │   │
│   │   ├── ingestion/               # Pipeline: file → vettori in Qdrant
│   │   │   ├── parser.py            # docling (PDF/DOCX) → unstructured (fallback) → openpyxl
│   │   │   ├── cleaner.py           # Pulizia testo: null bytes, page numbers, header/footer
│   │   │   ├── chunker.py           # MarkdownTextSplitter / RecursiveCharacterTextSplitter
│   │   │   ├── metadata.py          # Classificazione doc type + payload Qdrant
│   │   │   └── pipeline.py          # ★ Orchestratore: parse→clean→chunk→embed→upsert
│   │   │
│   │   ├── retrieval/
│   │   │   └── retriever.py         # ★ dense + sparse → RRF fusion → MMR → cross-encoder reranker
│   │   │
│   │   ├── generation/
│   │   │   ├── prompts.py           # Carica prompt da prompts.yaml + fallback hardcodati
│   │   │   ├── chain.py             # LangChain chain: context + prompt → LLM → risposta
│   │   │   ├── citations.py         # Estrae e formatta citazioni [Fonte N: file, p.X]
│   │   │   └── hallucination.py     # LLM-as-judge: score faithfulness 0.0-1.0
│   │   │
│   │   ├── memory/
│   │   │   ├── short_term.py        # Redis: ultimi N turni con TTL (ShortTermMemory class)
│   │   │   ├── long_term.py         # SQL: summary + fact extraction stile Zep (v2, off di default)
│   │   │   └── context_builder.py   # ★ Assembla: chunks + history + facts → prompt context
│   │   │
│   │   ├── agents/
│   │   │   ├── router_agent.py      # Classifica query: rag | web | sql | general
│   │   │   ├── web_agent.py         # Ricerca web: Tavily (preferito) | DDGS + LLM
│   │   │   └── tools/               # Tool singoli per gli agent (date, calculator, ecc.)
│   │   │
│   │   └── graph/                   # LangGraph workflow
│   │       ├── state.py             # RAGState TypedDict condiviso tra tutti i nodi
│   │       ├── nodes.py             # Un nodo per step: route, retrieve, generate, ecc.
│   │       ├── edges.py             # Logica routing condizionale post-route
│   │       └── graph.py             # ★ Assembla + compila grafo (singleton @lru_cache)
│   │
│   ├── services/                    # Orchestration layer: coordina DB + RAG + Redis
│   │   ├── chat_service.py          # ★ cache → retrieval → generation → memory → DB → stats
│   │   ├── document_service.py      # 🔥🔥TODO upload → hash check → DB → dispatch Celery job
│   │   └── tenant_service.py        # provision: SQL schema + Qdrant collection + admin user
│   │
│   ├── workers/                     # Celery tasks asincroni
│   │   ├── celery_app.py            # Factory Celery: code high/default/low/shared_cleanup
│   │   ├── ingestion_tasks.py       # ★ ingest_document: pipeline + retry backoff esponenziale
│   │   ├── cleanup_tasks.py         # purge_tenant (offboarding) + expire_sessions
│   │   └── scheduled_tasks.py       # rollup_usage giornaliero (celery-beat + redbeat)
│   │
│   └── schemas/                     # Pydantic v2 request/response — separati dai modelli DB
│       ├── common.py                # PaginatedResponse, ErrorResponse, SuccessResponse
│       ├── chat.py                  # ChatRequest, ChatResponse, MessageSchema, FeedbackRequest
│       └── document.py              # DocumentSchema, UploadResponse, IngestionJobSchema
│
│
├── tests/
│   ├── conftest.py                  # Fixtures condivise: app, client, tenant_context, sample_chunks
│   ├── unit/
│   │   ├── test_chunker.py          # TestCleaner, TestChunker, TestContextBuilder
│   │   └── test_security.py         # TestPasswordHashing, TestJWT, TestAPIKey
│   └── integration/
│       └── test_health.py           # Test /health e /ready endpoint
│
│
└── scripts/                         # Utility CLI
    ├── create_tenant.py             # python scripts/create_tenant.py --slug acme --name "Acme"
    ├── seed_demo_data.py            # Inserisce documenti demo per tenant demo-corp
    └── benchmark_retrieval.py       # Misura qualità RAG: keyword score + faithfulness score
```
---

## Flusso dati — dalla query alla risposta

```
Browser / Client
      ↓ HTTPS
   nginx (rev proxy, SSL, buffering off per SSE)
      ↓ :8000
   FastAPI (main.py)
      ↓
   Middleware stack (tenant → logging → rate_limit)
      ↓
   Route /chat/stream
      ↓
   ChatService.stream_query()
      ├── Redis: check cache query
      ├── Redis: load session (short-term memory)
      ├── retriever.retrieve()
      │     ├── fastembed: embed query
      │     ├── Qdrant: dense search (semantic)
      │     ├── Qdrant: sparse search (BM25)
      │     ├── RRF fusion
      │     ├── MMR diversification
      │     └── CrossEncoder: reranker (20→5 chunk)
      ├── context_builder.build_rag_context()
      ├── chain.astream_rag_chain() → LLM tokens via SSE
      ├── SQL Server: INSERT messages
      ├── Redis: append to session
      └── Redis: set query cache
```

## Flusso dati — upload documento

```
POST /api/v1/documents/upload
      ↓
   DocumentService.upload_and_queue()
      ├── SHA-256 hash → deduplication check SQL Server
      ├── Save file to /app/uploads/{tenant}/{uuid}.pdf
      ├── INSERT documents (status=pending) → SQL Server
      ├── INSERT ingestion_jobs (status=queued) → SQL Server
      └── ingest_document.apply_async(queue="default")
                              ↓
                        Celery Worker
                              ↓
                        ingestion_tasks.ingest_document()
                              ├── UPDATE status=running → SQL Server
                              ├── parser.parse_document() → docling/unstructured
                              ├── cleaner.clean_text()
                              ├── chunker.chunk_document()
                              ├── embeddings.embed_texts() → fastembed batch
                              ├── Qdrant: upsert points (batch 100)
                              ├── UPDATE status=done + chunk_count → SQL Server
                              └── Redis: invalidate query cache tenant
```

## Multi-tenant isolation — dove avviene

```
JWT payload
  {"tenant_id": "uuid", "tenant_slug": "acme", "role": "admin"}
      ↓
TenantMiddleware → request.state.tenant_id
      ↓
get_current_tenant() → TenantContext
      ↓
  ┌── get_db() → TenantDB.aget_session("acme")
  │               └── ALTER USER SA WITH DEFAULT_SCHEMA = [tenant_acme]
  │               └── ogni query trova automaticamente le tabelle di acme
  │
  ├── get_tenant_redis() → TenantRedis(tenant_id="uuid")
  │               └── ogni chiave prefissata: tenant:uuid:*
  │
  └── retriever.retrieve() → filtro Qdrant: tenant_id = "uuid"
                  └── vettori di altri tenant non vengono mai restituiti
```

---

## Conteggio file

| Area | File Python |
|---|---|
| app/core/ | 7 |
| app/api/ | 12 |
| app/db/ | 7 |
| app/rag/ | 16 |
| app/services/ | 3 |
| app/workers/ | 4 |
| app/schemas/ | 3 |
| tests/ | 5 |
| scripts/ | 3 |
| **Totale** | **60 file Python** |

| Area | File config/infra |
|---|---|
| config/ | 4 yaml |
| docker/ | 2 Dockerfile + 2 sql/sh |
| root | docker-compose x2, .env.example, pyproject.toml, requirements x2 |
| **Totale** | **14 file config/infra** |


Come funziona il flusso SSE end-to-end usando ChainLit x il frontend
```
  Browser → WebSocket → Chainlit (8080)
                            ↓ httpx POST /api/v1/chat/stream
                        FastAPI (8000)
                            ↓ stream_query() yields tokens
                            ↓ yield "\x1e{sources, conv_id}" [sentinel]
                        event_generator() intercetta →
                            data: {"token": "..."}   ×N
                            data: {"done": true, "sources": [...], "conversation_id": "..."}
                            ↓
                        Chainlit stream_token() → msg.update()
                        → mostra fonti come cl.Text elementi espandibili
```

  docker-compose up --build
  UI disponibile su http://localhost:8080
  Login: email + password + (opzionale) email|tenant-slug

SYSTEM DOCKER-COMPOSE

[fastapi container]
[redis container]
[sqlserver container]
[qdrant container]

[celery-worker-high container]
    ├── worker process 1
    ├── worker process 2
    ├── worker process 3
    ├── worker process 4

[celery-worker-default container]
    ├── worker process 1
    ├── worker process 2

[celery-beat container]

[flower container]

[chainlit container]

//x celery remember each servizio worker è un container che esegue più task in parallelo
//sistema facilemente scalabile (ovviamente per i containers Stateless sono facilmente scalabili, quelli Statefule e.g.qdrant è meglio usare cloud!)
//puoi fare e.g.'docker compose up --scale celery-worker-high=3' e ottenere 3 containers x celery-worker-high il quale ognuno ha 4 concurrency -> ottieni cosi in totale 12 processi totali!  
  
  ############################################

---
  1. Dove vengono salvati fisicamente i PDF?

  Problema critico: document_service.py è completamente VUOTO (0 bytes).

  La route POST /documents/upload (documents.py:53) chiama:
  await service.upload_and_queue(file_bytes=file_bytes, ...)
  ...ma DocumentService.upload_and_queue() non esiste — il file è empty. Questo significa che il caricamento PDF non funziona cosìcom'è.

  La pipeline di ingestion (pipeline.py:28) si aspetta un file_path: str assoluto sul filesystem, ma nessuno lo crea. L'unico esempio di salvataggio fisico
  funzionante è in scripts/seed_demo_data.py:93 con tempfile.NamedTemporaryFile, usato solo per i dati di seed (file temp cancellato dopo l'ingestion).

  Nel docker-compose non è definito nessun volume per gli upload — non c'è /app/uploads né simili. Devi:
  1. Implementare DocumentService.upload_and_queue() in app/services/document_service.py
  2. Decidere dove salvare i file: volume Docker dedicato (e.g. - uploads_data:/app/uploads) o storage esterno (S3/Azure Blob)
  3. Passare il file_path al task Celery ingest_document

  ---
  2. Context e metadata della chat — è tutto sistemato?

  Sì, la parte chat è ben strutturata. Il flusso è:

  ┌─────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────┐
  │                  Layer                  │                                       Cosa fa                                       │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Redis (short-term)                      │ Ultimi 10 turni per conversazione, TTL 24h                                          │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Context builder (context_builder.py:12) │ Assembla chunks RAG + history, cap a 12.000 chars                                   │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ SQL Server                              │ Salva permanentemente ogni messaggio con sources, tokens_in, tokens_out, latency_ms │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Cache Redis                             │ MD5(conv_id + question) → risposta cachata per 1h                                   │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
  │ Sentinel \x1e                           │ Separa i token dello stream dai metadati finali (sources, conversation_id) in SSE   │
  └─────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────┘

  Un caveat: nel chat_service.py (percorso diretto) il hallucination check non viene chiamato — solo nel grafo LangGraph (graph.py). Se usi ChatService.query() invece del grafo, i guardrail di
  allucinazione vengono saltati.


  Un caveat: nel chat_service.py (percorso diretto) il hallucination check non viene chiamato — solo nel grafo LangGraph (graph.py). Se usi ChatService.query() invece del grafo, i guardrail di
  allucinazione vengono saltati.


  Un caveat: nel chat_service.py (percorso diretto) il hallucination check non viene chiamato — solo nel grafo LangGraph (graph.py). Se usi ChatService.query()
  invece del grafo, i guardrail di allucinazione vengono saltati.

  ---
  3. Guardrail per risposte professionali?

  Sì, ci sono più livelli:

  Prompt (prompts.yaml:9-14):
  - "Sei preciso, professionale e citi sempre le fonti"
  - "Non inventare mai informazioni che non sono nei documenti"
  - "Usa ESCLUSIVAMENTE le seguenti sezioni di documenti"
  - "Se non trovi la risposta, dillo esplicitamente"

  Hallucination check (hallucination.py:11):
  - Score 0.0→1.0 calcolato dall'LLM stesso sul proprio output
  - Soglia is_hallucination() a 0.5 (hallucination.py:56)
  - Ma answer_validator.py è anch'esso vuoto (1 sola riga) — il grafo chiama solo check_faithfulness, non una validazione strutturata

  Riepilogo problemi aperti:
  1. document_service.py vuoto → upload PDF non funziona
  2. answer_validator.py vuoto → validazione risposta non implementata
  3. Hallucination check attivo solo nel grafo LangGraph, non nel path diretto ChatService

  ###########
  Fix applicati

  app/services/document_service.py

  - Rimosso UPLOAD_DIR.mkdir() a livello di modulo — causava crash all'import se /app/uploads non esisteva ancora (es. in CI o test). La directory viene ora
  creata lazily al momento del primo upload, con parents=True, exist_ok=True già presente nella riga file_path.parent.mkdir(...).

  app/services/chat_service.py — 3 modifiche

  1. Import di validate_answer e check_faithfulness/is_hallucination in testa al file.
  2. query() (non-streaming): dopo arun_rag_chain(), chiama validate_answer() (pulisce artefatti LLM, tronca, fallback se vuota) po
      268  #i volumes sono area persistente ESTERNA AL CONTAINER, su linux solitamente in /var/lib/docker/volumes/, su Windo
           ws Docker Desktop solitamente C:\Users\Username\AppData\Local\docker\volumes. LI GESTISCE DOCKER
      269  

● Verifico che tutto sia coerente leggendo le parti chiave dei file modificati:

  Read 1 file (ctrl+o to expand)

● Tutto corretto. Riepilogo di tutte le modifiche fatte:

  ---
  Fix applicati

  app/services/document_service.py

  - Rimosso UPLOAD_DIR.mkdir() a livello di modulo — causava crash all'import se /app/uploads non esisteva ancora (es. in CI o
  test). La directory viene ora creata lazily al momento del primo upload, con parents=True, exist_ok=True già presente nella riga
  file_path.parent.mkdir(...).

  app/services/chat_service.py — 3 modifiche

  1. Import di validate_answer e check_faithfulness/is_hallucination in testa al file.
  2. query() (non-streaming): dopo arun_rag_chain(), chiama validate_answer() (pulisce artefatti LLM, tronca, fallback se vuota)
  poi check_faithfulness() con warning log se score < 0.5.
  3. stream_query() (SSE): dopo che full_answer è completato, esegue gli stessi check; il hallucination_score viene incluso nel
  sentinel \x1e così il frontend lo riceve nel payload done.

  docker-compose.yml — 4 modifiche

  ┌───────────────────────┬──────────────────────────────────────────────────────────────────────┐
  │       Servizio        │                           Volume aggiunto                            │
  ├───────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ fastapi               │ uploads_data:/app/uploads — FastAPI scrive i PDF qui                 │
  ├───────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ celery-worker-default │ uploads_data:/app/uploads — critico: legge i PDF durante l'ingestion │
  ├───────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ celery-worker-high    │ uploads_data:/app/uploads — necessario per reprocess_document        │
  ├───────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ volumes: (section)    │ uploads_data: driver: local — definizione del volume named           │
  └───────────────────────┴──────────────────────────────────────────────────────────────────────┘

  Il volume è condiviso tra i tre container, quindi il path assoluto /app/uploads/{tenant_slug}/{document_id}.pdf che viene salvato
  da FastAPI e passato a Celery è sempre valido su tutti i nodi.

  ##########################

  Risultati audit completo

  4 bug trovati e fixati

  ---
  Bug 1 — Redbeat non attivato (app/workers/celery_app.py)

  redbeat_redis_url e redbeat_key_prefix erano presenti ma senza beat_scheduler = 'redbeat.RedBeatScheduler' Celery ignorava silenziosamente quelle
  impostazioni e usava il suo scheduler file-based di default (celerybeat-schedule locale). I task periodici funzionavano ma senza persistenza Redis —
  riavviando il container il clock si resettava.

  Fix: aggiunta una riga in conf.update(...):
  beat_scheduler="redbeat.RedBeatScheduler",

  ---
  Bug 2 — Tabella conversation_summaries mancante (docker/sqlserver/init.sql)

  Usata in conversation_repo.py (save_summary, get_recent_summaries) e in long_term.py (summarize_conversation, get_recent_summaries) ma la stored procedure
  sp_provision_tenant non la creava mai. Runtime error garantito con memory_long_term_enabled = true.

  Fix: aggiunto DDL nella stored procedure:
  id, conversation_id, user_id, summary_text, turn_count, from_turn, to_turn, created_at

  ---
  Bug 3 — Tabella user_facts mancante (docker/sqlserver/init.sql)

  Usata in long_term.py (_upsert_fact con MERGE, get_user_facts con SELECT). Stessa situazione: non creata in sp_provision_tenant.

  Fix: aggiunto DDL + index nella stored procedure:
  id, user_id, fact_type, fact_key, fact_value, confidence, is_active, source_conv_id, created_at, updated_at
  INDEX su (user_id, is_active, confidence DESC)

  ---
  Bug 4 (critico, bonus) — Utente SQL Server mai creato (docker/sqlserver/init.sql)

  sqlserver.py fa EXECUTE AS USER = N'usr_tenant_acme_corp' per lo schema switching session-scoped, ma il commento che diceva "creato da sp_provision_tenant"
  era falso — la stored procedure non creava mai quell'utente DB. Ogni singola request a qualsiasi endpoint tenant sarebbe crashata con un errore SQL di
  impersonation.

  Fix: aggiunto nella stored procedure:
  CREATE USER [usr_tenant_X] WITHOUT LOGIN WITH DEFAULT_SCHEMA = [tenant_X]
  GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::[tenant_X] TO [usr_tenant_X]

  ---
  Review generale app — nessun altro bug critico

  Il resto dell'app è solido:
  - deps.py: get_db() → aget_session() gestisce correttamente commit/rollback/REVERT
  - chat_service.py: flusso cache → retrieval → generation → hallucination check → save → Redis corretto; il commit() implicito arriva dalla fine di
  aget_session()
  - redis_client.py: async corretto, pipeline() usato bene, namespace isolation per tenant funziona
  - cleanup_tasks.py / scheduled_tasks.py: tutti i path sync Celery hanno session.commit() esplicito

  Osservazione non critica: ChatService._save_messages() non ha il parametro hallucination_score — il punteggio viene calcolato, loggato e inviato al client
  CREATE USER [usr_tenant_X] WITHOUT LOGIN WITH DEFAULT_SCHEMA = [tenant_X]
  GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::[tenant_X] TO [usr_tenant_X]

  ---
  Review generale app — nessun altro bug critico

  Il resto dell'app è solido:
  - deps.py: get_db() → aget_session() gestisce correttamente commit/rollback/REVERT
  - chat_service.py: flusso cache → retrieval → generation → hallucination check → save → Redis corretto; il commit() implicito arriva dalla fine di
  aget_session()
  - redis_client.py: async corretto, pipeline() usato bene, namespace isolation per tenant funziona
  - cleanup_tasks.py / scheduled_tasks.py: tutti i path sync Celery hanno session.commit() esplicito

  Osservazione non critica: ChatService._save_messages() non ha il parametro hallucination_score — il punteggio viene calcolato, loggato e inviato al client
  nel sentinel SSE, ma non viene mai persistito nel campo messages.hallucination_score di SQL Server. Non è un runtime error, ma è un dato che va perso.
