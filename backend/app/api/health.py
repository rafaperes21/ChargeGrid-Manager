from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Verifica se a API esta no ar")
def health() -> dict[str, str]:
    return {"status": "ok"}
