# PLANO DE BACKPORT — Correções feitas no monorepo ecossistema-aidd

> **Origem:** `C:\Users\trcnologia\Desktop\ecossistema-aidd\tools\aidd-master-enterprise`
> **Repositório:** `heverton-dev/aidd-master-enterprise` (padrão neste repositório)
> **Status:** PRONTO PARA EXECUÇÃO
> **Dificuldade:** Média — precisa de Docker Desktop rodando para validar 1 dos 3 fixes

---

## 1. CONTEXTO

Mesma origem do plano do `aidd-generator`: cópia deste repositório dentro do monorepo `ecossistema-aidd`, auditada e corrigida lá, nunca trazida de volta pra cá. `diff` direto confirmou que os 3 bugs abaixo existem aqui também.

## 2. O QUE MUDA

### 2.1. `requirements.txt` — dependência real faltando

`tests/unit/test_events_driver.py::test_redis_driver_raises_clear_error_message_when_url_invalid_scheme` precisa do pacote `redis` instalado pra sequer instanciar `RedisStreamsDriver` (o produto trata `redis` como opcional, mas o teste depende dele estar presente). Nunca esteve listado.

**Mudança:** adicionar `redis>=5.0.0` ao `requirements.txt`.

### 2.2. `scripts/scaffold_infra.py` — bug real de template Helm (linha ~249)

```
resources: {{ toYaml .Values.resources }}
```
`toYaml` produz YAML multi-linha; inline sem quebra/indentação gera YAML **inválido de verdade** (`helm lint` reprova com "mapping values are not allowed in this context"). Confirmado gerando o chart e inspecionando a saída — não é suposição.

**Mudança:**
```
resources:
  {{- toYaml .Values.resources | nindent 12 }}
```

### 2.3. `tests/unit/test_events_driver.py` — race condition real em teste de integração Docker+Redis

`test_event_emitted_on_instance_a_is_processed_on_instance_b_via_redis` sobe um container `redis:7` real. O loop de espera só verificava se conseguia **construir** `RedisStreamsDriver` — mas `redis.from_url()` é preguiçoso (não conecta de fato), então essa checagem nunca prova que o servidor está pronto. O primeiro comando real (`xgroup_create`, dentro de `.on()`) fica sem nenhuma proteção contra a janela estreita logo após o container subir.

**Mudança:** dentro do loop de retry, depois de construir cada `RedisStreamsDriver`, chamar `driver._redis.ping()` antes de prosseguir — força o primeiro round-trip de verdade.

## 3. COMO APLICAR

Copiar de `ecossistema-aidd/tools/aidd-master-enterprise/`:
- `requirements.txt`
- `scripts/scaffold_infra.py`
- `tests/unit/test_events_driver.py`

## 4. VALIDAÇÃO (critério de aceite — nesta ordem)

```bash
pip install -r requirements.txt
python -m pytest -q
```
Esperado: `helm`/`terraform` vão aparecer como `SKIPPED` se não estiverem instalados nesta máquina (comportamento correto, não é falha).

**Se o Docker Desktop estiver rodando**, validar o fix do item 2.3 de verdade (não confiar só na leitura do código):
```bash
docker rmi redis:7   # forca imagem fria, testa o cenario mais dificil
python -m pytest tests/unit/test_events_driver.py::test_event_emitted_on_instance_a_is_processed_on_instance_b_via_redis -v
```
Esperado: `PASSED`. Rodar pelo menos 2-3 vezes (com `docker rmi redis:7` entre cada uma) pra ter confiança — é teste de race condition, uma passada só não prova nada.

## 5. COMMIT E PUSH

Commit único, mensagem no mesmo padrão do monorepo, depois `git push origin main`.
