import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, func, update
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel


class IngestionBatchStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


class IngestionBatch(SQLModel, table=True):

    __tablename__ = "ingestion_batches"
    __table_args__ = (
        Index("ix_ingestion_batches_id", "id"),
        {"comment": "Tracks each CSV ingestion request for audit and traceability"},
    )

    id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Unique batch identifier")
    )
    status: IngestionBatchStatus = Field(
        sa_column=Column(SAEnum(IngestionBatchStatus, name="ingestion_batch_status"), nullable=False, default=IngestionBatchStatus.pending, comment="Ingestion status")
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="Timestamp when the batch was created"),
    )


class AuditMixin(SQLModel):
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="Row creation timestamp"),
    )
    batch_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("ingestion_batches.id"), nullable=False, comment="Ingestion batch this row belongs to"),
    )


class Departments(AuditMixin, SQLModel, table=True):

    __tablename__ = "departments"
    __table_args__ = (
        Index("ix_departments_id", "id"),
        {"comment": "Company departments"},
    )

    id: int = Field(sa_column=Column(Integer, primary_key=True, comment="Id of the department"))
    department: str = Field(sa_column=Column(String, nullable=False, comment="Name of the department"))


class Jobs(AuditMixin, SQLModel, table=True):

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_id", "id"),
        {"comment": "Available job positions"},
    )

    id: int = Field(sa_column=Column(Integer, primary_key=True, comment="Id of the job"))
    job: str = Field(sa_column=Column(String, nullable=False, comment="Name of the job position"))


class Employees(AuditMixin, SQLModel, table=True):

    __tablename__ = "employees"
    __table_args__ = (
        Index("ix_employees_id", "id"),
        {"comment": "Historical hired employees"},
    )

    id: int = Field(sa_column=Column(Integer, primary_key=True, comment="Id of the employee"))
    name: str = Field(sa_column=Column(String, nullable=False, comment="Name and surname of the employee"))
    hiring_datetime: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, comment="Hire datetime in ISO format"))
    department_id: int = Field(sa_column=Column(Integer, ForeignKey("departments.id"), nullable=False, comment="Id of the department which the employee was hired for"))
    job_id: int = Field(sa_column=Column(Integer, ForeignKey("jobs.id"), nullable=False, comment="Id of the job which the employee was hired for"))
