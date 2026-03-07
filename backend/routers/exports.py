import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from database import db_dependency

logger = logging.getLogger(__name__)
router = APIRouter()


async def _export(db, export_type: str, property_id: Optional[str] = None) -> FileResponse:
    from export_engine import export_to_excel
    filters = {}
    if property_id:
        filters["property_id"] = property_id
    try:
        filepath = await export_to_excel(db, export_type, filters)
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")

    import os
    filename = os.path.basename(filepath)
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


@router.get("/exports/open-issues")
async def export_open_issues(property_id: Optional[str] = None, db=Depends(db_dependency)):
    return await _export(db, "open_issues", property_id)


@router.get("/exports/tenant-contacts")
async def export_tenant_contacts(property_id: Optional[str] = None, db=Depends(db_dependency)):
    return await _export(db, "tenant_contacts", property_id)


@router.get("/exports/overdue-responses")
async def export_overdue_responses(property_id: Optional[str] = None, db=Depends(db_dependency)):
    return await _export(db, "overdue_responses", property_id)


@router.get("/exports/property-report")
async def export_property_report(db=Depends(db_dependency)):
    return await _export(db, "property_report")
