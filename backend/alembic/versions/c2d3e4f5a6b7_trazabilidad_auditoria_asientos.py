"""trazabilidad_auditoria_asientos

Revision ID: c2d3e4f5a6b7
Revises: bb1c920e98ab
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'bb1c920e98ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('asiento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('creado_por_usuario_id', sa.Integer(), sa.ForeignKey('usuario.id', ondelete='RESTRICT'), nullable=True))
        batch_op.add_column(sa.Column('asentado_por_usuario_id', sa.Integer(), sa.ForeignKey('usuario.id', ondelete='RESTRICT'), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('asentado_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('version', sa.Integer(), server_default='1', nullable=False))
        batch_op.create_index('ix_asiento_ejercicio_estado_fecha', ['ejercicio_id', 'estado', 'fecha'])

    # Backfill para filas preexistentes si las hubiera
    op.execute(
        "UPDATE asiento SET creado_por_usuario_id = (SELECT id FROM usuario LIMIT 1), created_at = CURRENT_TIMESTAMP WHERE creado_por_usuario_id IS NULL"
    )

    with op.batch_alter_table('asiento', schema=None) as batch_op:
        batch_op.alter_column('creado_por_usuario_id', nullable=False)
        batch_op.alter_column('created_at', nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('asiento', schema=None) as batch_op:
        batch_op.drop_index('ix_asiento_ejercicio_estado_fecha')
        batch_op.drop_column('version')
        batch_op.drop_column('asentado_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('asentado_por_usuario_id')
        batch_op.drop_column('creado_por_usuario_id')
