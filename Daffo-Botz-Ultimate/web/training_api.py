import time
import uuid
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import Field

from bot.training import Conflict, Dataset, Document, Evaluation, Example, Profile, StrictModel


class Revision(StrictModel):
    revision: int = Field(ge=0)


class Publish(Revision):
    label: str = Field(default='Pembaruan pengetahuan', min_length=1, max_length=100)


class Restore(Revision):
    version: str = Field(pattern=r'^[a-f0-9]{32}$')


class SaveProfile(Revision):
    profile: Profile


class SaveDocument(Revision):
    document: Document


class SaveExample(Revision):
    example: Example


class SaveEvaluation(Revision):
    evaluation: Evaluation


class Import(Revision):
    dataset: Dataset


class Preview(StrictModel):
    prompt: str = Field(min_length=1, max_length=2000)
    mode: Literal['draft', 'active'] = 'draft'
    generate: bool = False


class Evaluate(StrictModel):
    mode: Literal['draft', 'active'] = 'draft'
    generate: bool = False


def register_training(app, session):
    def training():
        return app.state.store.training

    async def run_mutation(operation, clear_memory=False):
        try:
            result = await operation
            if clear_memory:
                app.state.bot.ai.clear()
            return result
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get('/api/training')
    async def overview(auth=Depends(session)):
        return await training().overview()

    @app.put('/api/training/profile')
    async def profile(data: SaveProfile, auth=Depends(session)):
        dataset = training().draft.model_copy(deep=True)
        dataset.profile = data.profile
        return await run_mutation(training().save(dataset, data.revision))

    async def upsert(kind, entry, revision):
        dataset = training().draft.model_copy(deep=True)
        entries = getattr(dataset, kind)
        index = next((i for i, item in enumerate(entries) if item.id == entry.id), None)
        if index is None:
            limit = 30 if kind == 'evaluations' else 100
            if len(entries) >= limit:
                raise HTTPException(422, f'Maksimal {limit} entri.')
            entries.append(entry)
        else:
            entries[index] = entry
        return await run_mutation(training().save(dataset, revision))

    @app.post('/api/training/documents')
    async def documents(data: SaveDocument, auth=Depends(session)):
        return await upsert('documents', data.document, data.revision)

    @app.post('/api/training/examples')
    async def examples(data: SaveExample, auth=Depends(session)):
        return await upsert('examples', data.example, data.revision)

    @app.post('/api/training/evaluations')
    async def cases(data: SaveEvaluation, auth=Depends(session)):
        return await upsert('evaluations', data.evaluation, data.revision)

    @app.delete('/api/training/{kind}/{entry_id}')
    async def remove(kind: Literal['documents', 'examples', 'evaluations'], entry_id: str, data: Revision, auth=Depends(session)):
        dataset = training().draft.model_copy(deep=True)
        entries = getattr(dataset, kind)
        if not any(e.id == entry_id for e in entries):
            raise HTTPException(404, 'Entri tidak ditemukan.')
        setattr(dataset, kind, [e for e in entries if e.id != entry_id])
        return await run_mutation(training().save(dataset, data.revision))

    @app.post('/api/training/publish')
    async def publish(data: Publish, auth=Depends(session)):
        result = await run_mutation(training().publish(data.revision, data.label), clear_memory=True)
        app.state.bot.log('Admin menerbitkan versi pengetahuan baru.')
        return result

    @app.post('/api/training/rollback')
    async def rollback(data: Restore, auth=Depends(session)):
        result = await run_mutation(training().rollback(data.version, data.revision), clear_memory=True)
        app.state.bot.log('Admin memulihkan versi pengetahuan.')
        return result

    @app.get('/api/training/export')
    async def export(auth=Depends(session)):
        return training().draft.model_dump()

    @app.post('/api/training/import')
    async def import_dataset(data: Import, auth=Depends(session)):
        return await run_mutation(training().save(data.dataset, data.revision))

    async def generate(prompt, draft):
        key = ('studio', uuid.uuid4().hex)
        try:
            return await app.state.bot.ai.ask(key, prompt, 'Simulasi admin; jangan mengirim pesan atau menjalankan aksi WhatsApp.', knowledge_draft=draft)
        finally:
            app.state.bot.ai.clear(key)

    @app.post('/api/training/preview')
    async def preview(data: Preview, auth=Depends(session)):
        if auth['test_lock'].locked():
            raise HTTPException(429, 'Satu uji AI masih berjalan.')
        async with auth['test_lock']:
            started = time.monotonic()
            _, sources = training().context(data.prompt, data.mode == 'draft')
            try:
                answer = await generate(data.prompt, data.mode == 'draft') if data.generate else None
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            return {'answer': answer, 'sources': sources, 'mode': data.mode, 'revision': training().revision,
                    'latency_ms': round((time.monotonic() - started) * 1000)}

    @app.post('/api/training/evaluate')
    async def evaluate(data: Evaluate, auth=Depends(session)):
        if auth['test_lock'].locked():
            raise HTTPException(429, 'Satu uji AI masih berjalan.')
        # Capture a consistent dataset. Prevent concurrent publication while a
        # live suite uses it; bounded to ten cases and shown as substring checks.
        async with auth['test_lock'], app.state.store.lock:
            dataset = training().draft if data.mode == 'draft' else training().active
            cases = list(dataset.evaluations)
            if not cases:
                raise HTTPException(422, 'Tambahkan kasus evaluasi terlebih dahulu.')
            if data.generate and len(cases) > 10:
                raise HTTPException(422, 'Uji AI maksimal 10 kasus. Uji retrieval mendukung 30 kasus.')
            results = []
            for case in cases:
                _, sources = training().context(case.question, data.mode == 'draft')
                try:
                    answer = await generate(case.question, data.mode == 'draft') if data.generate else '\n'.join(s['text'] for s in sources)
                    expected = [term.strip().casefold() for term in case.expected.split(',') if term.strip()]
                    matched = [term for term in expected if term in answer.casefold()]
                    results.append({'id': case.id, 'question': case.question, 'passed': bool(expected) and len(matched) == len(expected),
                                    'matched': matched, 'expected': expected, 'answer': answer, 'sources': sources})
                except ValueError as exc:
                    results.append({'id': case.id, 'question': case.question, 'passed': False, 'error': str(exc)})
            return {'mode': 'ai' if data.generate else 'retrieval', 'passed': sum(r['passed'] for r in results),
                    'total': len(results), 'results': results, 'revision': training().revision}
