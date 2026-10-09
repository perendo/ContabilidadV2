"""trazabilidad_auditoria_asientos

Revision ID: c2d3e4f5a6b7
Revises: bb1c920e98ab
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'bb1c920e98ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def upgrade() -> None:
    # Limpieza defensiva ante intentos previos fallidos en SQLite
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_asiento")

    with op.batch_alter_table('asiento', schema=None, naming_convention=naming_convention) as batch_op:
        batch_op.add_column(sa.Column('creado_por_usuario_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('asentado_por_usuario_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('asentado_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('version', sa.Integer(), server_default='1', nullable=False))
        batch_op.create_foreign_key(
            'fk_asiento_creado_por_usuario_id',
            'usuario',
            ['creado_por_usuario_id'],
            ['id'],
            ondelete='RESTRICT',
        )
        batch_op.create_foreign_key(
            'fk_asiento_asentado_por_usuario_id',
            'usuario',
            ['asentado_por_usuario_id'],
            ['id'],
            ondelete='RESTRICT',
        )
        batch_op.create_index('ix_asiento_ejercicio_estado_fecha', ['ejercicio_id', 'estado', 'fecha'])

    # Backfill para filas preexistentes si las hubiera
    op.execute(
        "UPDATE asiento SET creado_por_usuario_id = (SELECT id FROM usuario LIMIT 1), created_at = CURRENT_TIMESTAMP WHERE creado_por_usuario_id IS NULL"
    )

    with op.batch_alter_table('asiento', schema=None, naming_convention=naming_convention) as batch_op:
        batch_op.alter_column('creado_por_usuario_id', nullable=False)
        batch_op.alter_column('created_at', nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('asiento', schema=None, naming_convention=naming_convention) as batch_op:
        batch_op.drop_index('ix_asiento_ejercicio_estado_fecha')
        batch_op.drop_constraint('fk_asiento_asentado_por_usuario_id', type_='foreignkey')
        batch_op.drop_constraint('fk_asiento_creado_por_usuario_id', type_='foreignkey')
        batch_op.drop_column('version')
        batch_op.drop_column('asentado_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('asentado_por_usuario_id')
        batch_op.drop_column('creado_por_usuario_id')
