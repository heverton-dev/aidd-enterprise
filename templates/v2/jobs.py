# -*- coding: utf-8 -*-
"""
=============================================================================
AIDD v4.1 Enterprise — FILA DE PROCESSAMENTO ASSÍNCRONO (JobQueue)
=============================================================================
Executa tarefas em background (envio de webhooks, geração de relatórios, etc.)
sem bloquear requisições HTTP do servidor principal.
"""

import queue
import threading
import time
import uuid
from typing import Callable, Any, Dict, Optional


class JobQueue:
    def __init__(self, max_workers: int = 2):
        self._queue: queue.Queue = queue.Queue()
        self._workers = []
        self._running = True
        self._jobs_status: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        for i in range(max_workers):
            t = threading.Thread(target=self._worker_loop, name=f"AIDD-JobWorker-{i}", daemon=True)
            t.start()
            self._workers.append(t)

    def enqueue(self, func: Callable, *args, **kwargs) -> str:
        """Enfileira uma tarefa assíncrona e retorna o ID do Job."""
        job_id = str(uuid.uuid4())
        job_info = {
            "id": job_id,
            "status": "ENFILEIRADO",
            "criado_em": time.time(),
            "iniciado_em": None,
            "concluido_em": None,
            "resultado": None,
            "erro": None
        }
        with self._lock:
            self._jobs_status[job_id] = job_info

        self._queue.put((job_id, func, args, kwargs))
        return job_id

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retorna o status atual de uma tarefa."""
        with self._lock:
            return self._jobs_status.get(job_id)

    def _worker_loop(self):
        while self._running:
            try:
                job_id, func, args, kwargs = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            with self._lock:
                if job_id in self._jobs_status:
                    self._jobs_status[job_id]["status"] = "PROCESSANDO"
                    self._jobs_status[job_id]["iniciado_em"] = time.time()

            try:
                res = func(*args, **kwargs)
                with self._lock:
                    if job_id in self._jobs_status:
                        self._jobs_status[job_id]["status"] = "CONCLUIDO"
                        self._jobs_status[job_id]["concluido_em"] = time.time()
                        self._jobs_status[job_id]["resultado"] = res
            except Exception as e:
                with self._lock:
                    if job_id in self._jobs_status:
                        self._jobs_status[job_id]["status"] = "FALHOU"
                        self._jobs_status[job_id]["concluido_em"] = time.time()
                        self._jobs_status[job_id]["erro"] = str(e)
            finally:
                self._queue.task_done()
