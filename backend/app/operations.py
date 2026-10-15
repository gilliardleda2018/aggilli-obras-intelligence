from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import Project, Membership, AuditEvent, Expense, Payment
from .measurements import access
from .security import require_identity

router = APIRouter(prefix="/api/v1",tags=["operations"])

class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1,max_length=300)
    supplier: str = Field(min_length=1,max_length=200)
    amount: Decimal = Field(gt=0,decimal_places=2)
    category: str = Field(pattern="^(MATERIAL|LABOR|FUEL|EQUIPMENT|SERVICE|OTHER)$")
    evidence_key: str | None = Field(default=None,max_length=500)

class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0,decimal_places=2)
    scheduled_date: date

class ConfirmPayment(BaseModel):
    reference: str = Field(min_length=3,max_length=200)

@router.post("/projects/{project_id}/expenses",status_code=201)
def create_expense(project_id:str,payload:ExpenseCreate,subject:str=Depends(require_identity),
                   db:Session=Depends(get_db)):
    project=access(db,subject,project_id,["OWNER","ADMIN","ENGINEER","FIELD_OPERATOR"])
    item=Expense(project_id=project.id,created_by=subject,**payload.model_dump())
    db.add(item);db.flush()
    db.add(AuditEvent(organization_id=project.organization_id,subject_id=subject,
                      action="expense.create",resource_id=item.id))
    db.commit()
    return {"id":item.id,"status":item.status}

@router.get("/projects/{project_id}/expenses")
def list_expenses(project_id:str,subject:str=Depends(require_identity),db:Session=Depends(get_db)):
    access(db,subject,project_id,["OWNER","ADMIN","ENGINEER","INSPECTOR","FIELD_OPERATOR","VIEWER"])
    rows=db.scalars(select(Expense).where(Expense.project_id==project_id)).all()
    return [{"id":x.id,"description":x.description,"supplier":x.supplier,
             "amount":str(x.amount),"category":x.category,"status":x.status,
             "evidence_key":x.evidence_key} for x in rows]

@router.post("/expenses/{expense_id}/payments",status_code=201)
def schedule_payment(expense_id:str,payload:PaymentCreate,subject:str=Depends(require_identity),
                     db:Session=Depends(get_db)):
    expense=db.get(Expense,expense_id)
    if expense is None: raise HTTPException(status_code=404,detail="Expense not found")
    project=access(db,subject,expense.project_id,["OWNER","ADMIN"])
    # Lock expense to serialize payment scheduling.
    expense=db.scalar(select(Expense).where(Expense.id==expense_id).with_for_update())
    committed=db.scalar(select(func.coalesce(func.sum(Payment.amount),0)).where(
        Payment.expense_id==expense_id,Payment.status.in_(["SCHEDULED","PAID"])))
    if Decimal(str(committed))+payload.amount>expense.amount:
        raise HTTPException(status_code=409,detail="Expense balance exceeded")
    payment=Payment(expense_id=expense.id,amount=payload.amount,
                    scheduled_date=payload.scheduled_date,created_by=subject)
    db.add(payment);db.flush()
    db.add(AuditEvent(organization_id=project.organization_id,subject_id=subject,
                      action="payment.schedule",resource_id=payment.id))
    db.commit()
    return {"id":payment.id,"status":payment.status}

@router.post("/payments/{payment_id}/confirm")
def confirm_payment(payment_id:str,payload:ConfirmPayment,subject:str=Depends(require_identity),
                    db:Session=Depends(get_db)):
    payment=db.get(Payment,payment_id)
    if payment is None: raise HTTPException(status_code=404,detail="Payment not found")
    expense=db.get(Expense,payment.expense_id)
    project=access(db,subject,expense.project_id,["OWNER","ADMIN"])
    payment=db.scalar(select(Payment).where(Payment.id==payment_id).with_for_update())
    if payment.status!="SCHEDULED":
        raise HTTPException(status_code=409,detail="Payment already decided")
    payment.status="PAID";payment.reference=payload.reference;payment.confirmed_by=subject
    db.add(AuditEvent(organization_id=project.organization_id,subject_id=subject,
                      action="payment.confirm",resource_id=payment.id))
    db.commit()
    return {"id":payment.id,"status":payment.status}

@router.get("/projects/{project_id}/payments")
def list_payments(project_id:str,subject:str=Depends(require_identity),db:Session=Depends(get_db)):
    access(db,subject,project_id,["OWNER","ADMIN","ENGINEER","INSPECTOR","VIEWER"])
    rows=db.execute(select(Payment,Expense).join(Expense,Payment.expense_id==Expense.id)
        .where(Expense.project_id==project_id)).all()
    return [{"id":p.id,"expense_id":e.id,"supplier":e.supplier,"amount":str(p.amount),
             "scheduled_date":p.scheduled_date.isoformat(),"status":p.status,
             "reference":p.reference} for p,e in rows]
