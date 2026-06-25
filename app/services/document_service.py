# =============================================================
# app/services/document_service.py
# Coordina upload → DB → dispatch Celery job.
# =============================================================

from __future__ import annotations
import hashlib
import os
import shutil
from pathlib import Path
from uuid import uuid4
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.settings import get_settings


settings = get_settings()

UPLOAD_DIR = Path("/app/uploads")   #dir dove salvare i file uploadati (creata lazily al primo upload). in docker-compose.yml mappa questa dir con volume locale per persistenza

class DocumentService:

    def __init__(self, db: AsyncSession, tenant_id: str, tenant_slug: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.user_id = user_id

    async def upload_and_queue(
        self,
        file_bytes: bytes,
        original_filename: str,
        collection_id: str | None = None,
    ) -> dict:
        """
        Salva il file, crea record DB, dispatcha job Celery.
        Returns:
            dict con document_id, job_id, task_id
        """
        # Validazione dimensione
        max_bytes = settings.ingestion_max_file_mb * 1024 * 1024  #100 iniziali, che diventa 104.857.600 bytes (è +-104.86 MB)
        if len(file_bytes) > max_bytes:
            raise ValueError(
                f"File troppo grande: { len(file_bytes) // 1024 // 1024 }MB "
                f"(max {settings.ingestion_max_file_mb}MB)"
            )
        file_hash = hashlib.sha256(file_bytes).hexdigest()  #trasforma in stringa esadecimale, hash SHA-256 per deduplicazione
        existing = await self.db.execute(
            text("SELECT id FROM documents WHERE file_hash = :hash"),
            {"hash": file_hash}
        )
        if existing.fetchone():
            raise ValueError(f"Documento già caricato: {original_filename}")
        #now save on disk
        document_id = str(uuid4())
        suffix = Path(original_filename).suffix  #.suffix restituisce estensione del file (e.g.'.pdf')
        saved_filename = f"{document_id}{suffix}"
        file_path = UPLOAD_DIR / self.tenant_slug / saved_filename  #create path tenant-scoped, e.g. /app/uploads/demo-corp/xxx.pdf
        file_path.parent.mkdir(parents=True, exist_ok=True)  #lazy:crea solo al primo upload. crea il folder(se non esiste ancora) che conterra il file, e.g. /app/uploads/demo-corp/...  crea fisicamente il folder 'demo-corp'. cosi ora il path UPLOAD_DIR / self.tenant_slug / saved_filename tutti sono fisici.
        with open(file_path, "wb") as f:  #wb: write binary
            f.write(file_bytes)     #scrivi fisicamente 
        # Determina mime type
        import mimetypes   #x provare a capiro il tipo del file guardando l'estensione 
        mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"   #e.g. mimetypes.guess_type("document.pdf")  return tupla (mime_type, encoding) quindi ("application/pdf", None), con [0] prendi solo il primo elemento. application/octet-stream è il MIME type generico per file binari sconosciuti.

        await self.db.execute(    #crea record in tab documents
            text("""
                INSERT INTO documents
                    (id, collection_id, filename, original_name, file_hash,
                     file_size, mime_type, storage_path, status, uploaded_by)
                VALUES
                    (:id, :coll_id, :filename, :orig_name, :hash,
                     :size, :mime, :path, 'pending', :user_id)
            """),
            {
                "id": document_id,
                "coll_id": collection_id,
                "filename": saved_filename,
                "orig_name": original_filename,
                "hash": file_hash,
                "size": len(file_bytes),
                "mime": mime_type,
                "path": str(file_path),
                "user_id": self.user_id,
            }
        )
        job_id = str(uuid4())
        await self.db.execute(    #crea record in tab ingestion_jobs
            text("""
                INSERT INTO ingestion_jobs (id, document_id, status)
                VALUES (:id, :doc_id, 'queued')
            """),
            {"id": job_id, "doc_id": document_id}
        )
        from app.workers.ingestion_tasks import ingest_document
        task = ingest_document.apply_async(    #dispatch task Celery sulla coda default
            args=[
                self.tenant_id,
                self.tenant_slug,
                document_id,
                str(file_path),
                collection_id,
            ],
            queue="default",
            headers={"tenant_id": self.tenant_id},
        )
        logger.info(
            "Documento in coda",
            document_id=document_id,
            filename=original_filename,
            task_id=task.id,
        )
        return {
            "document_id": document_id,
            "job_id": job_id,
            "task_id": task.id,
            "status": "queued",
        }

