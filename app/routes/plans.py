from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.utils.role_handle import require_admin
from app.controllers import plan_controller
from app.models.plan_model import PlanCreate, PlanOut, PlanUpdate

router = APIRouter(prefix="/plans", tags=["Plans"])

# ------------------ Public Endpoints ------------------

# View all plans
@router.get("/", response_model=List[PlanOut])
def get_all():
    return plan_controller.get_all_plans()

# ------------------ Admin Endpoints ------------------

# Create a plan
@router.post("/", response_model=PlanOut)
def create(plan: PlanCreate, current_user: dict = Depends(require_admin)):
    return plan_controller.create_plan(plan)

# Update a plan (partial update)
@router.patch("/{plan_id}", response_model=PlanOut)
def update_partial_plan(
    plan_id: int,
    plan_update: PlanUpdate,
    current_user: dict = Depends(require_admin)
):
    updated_plan = plan_controller.update_plan_partial(plan_id, plan_update)
    if not updated_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return updated_plan

# Delete a plan
@router.delete("/{plan_id}")
def delete(plan_id: int, current_user: dict = Depends(require_admin)):
    return plan_controller.delete_plan(plan_id)
