import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_notebook
from app.db.session import get_db
from app.models.output import GeneratedOutput
from app.models.workspace import Notebook
from app.schemas.output import OutputGenerateRequest, OutputOut
from app.workers.tasks import generate_output

router = APIRouter(prefix="/notebooks/{notebook_id}/outputs", tags=["outputs"])

_DEFAULT_TITLES = {
    "summary": "Summary",
    "faq": "FAQ",
    "study_guide": "Study Guide",
    "briefing": "Briefing Doc",
    "timeline": "Timeline",
}


@router.get("", response_model=list[OutputOut])
async def list_outputs(
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> list[GeneratedOutput]:
    result = await db.execute(
        select(GeneratedOutput)
        .where(GeneratedOutput.notebook_id == notebook.id)
        .order_by(GeneratedOutput.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=OutputOut, status_code=status.HTTP_202_ACCEPTED)
async def create_output(
    payload: OutputGenerateRequest,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> GeneratedOutput:
    """Create an output placeholder and queue LLM generation over the notebook's sources."""
    output = GeneratedOutput(
        notebook_id=notebook.id,
        type=payload.type,
        title=payload.title or _DEFAULT_TITLES.get(payload.type.value, "Output"),
        content="",
        params=payload.params,
    )
    db.add(output)
    await db.commit()
    generate_output.delay(str(output.id))
    return output


@router.get("/{output_id}", response_model=OutputOut)
async def get_output(
    output_id: uuid.UUID,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> GeneratedOutput:
    result = await db.execute(
        select(GeneratedOutput).where(
            GeneratedOutput.id == output_id,
            GeneratedOutput.notebook_id == notebook.id,
        )
    )
    output = result.scalar_one_or_none()
    if output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output not found")
    return output
