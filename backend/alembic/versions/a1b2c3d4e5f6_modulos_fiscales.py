"""modulos fiscales: factura, linea_factura_iva, liquidacion IS, fichero_presentacion

Revision ID: a1b2c3d4e5f6
Revises: 6b69941fa552
Create Date: 2026-10-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6b69941fa552'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('factura',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ejercicio_id', sa.Integer(), nullable=False),
    sa.Column('origen', sa.String(length=10), nullable=False),
    sa.Column('numero', sa.String(length=50), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('fecha_operacion', sa.Date(), nullable=True),
    sa.Column('tercero_cif', sa.String(length=9), nullable=False),
    sa.Column('tercero_razon_social', sa.String(length=200), nullable=False),
    sa.Column('solo_identificativo', sa.Boolean(), nullable=False),
    sa.Column('tipo_retencion', sa.String(length=3), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('notas', sa.String(length=1000), nullable=True),
    sa.Column('asiento_id', sa.Integer(), nullable=True),
    sa.Column('creado_por_usuario_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asiento_id'], ['asiento.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['creado_por_usuario_id'], ['usuario.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['ejercicio_id'], ['ejercicio.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ejercicio_id', 'tercero_cif', 'numero', name='uq_factura_ejercicio_cif_numero')
    )
    with op.batch_alter_table('factura', schema=None) as batch_op:
        batch_op.create_index('ix_factura_ejercicio_fecha', ['ejercicio_id', 'fecha'], unique=False)
        batch_op.create_index('ix_factura_ejercicio_origen', ['ejercicio_id', 'origen'], unique=False)

    op.create_table('linea_factura_iva',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('factura_id', sa.Integer(), nullable=False),
    sa.Column('numero_linea', sa.Integer(), nullable=False),
    sa.Column('descripcion', sa.String(length=300), nullable=False),
    sa.Column('base_imponible', sa.Numeric(precision=19, scale=2), nullable=False),
    sa.Column('tipo_iva', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('cuota_iva', sa.Numeric(precision=19, scale=2), nullable=False),
    sa.Column('tipo_re', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('cuota_re', sa.Numeric(precision=19, scale=2), nullable=True),
    sa.Column('operacion_exenta', sa.Boolean(), nullable=False),
    sa.Column('base_retencion', sa.Numeric(precision=19, scale=2), nullable=True),
    sa.Column('pct_retencion', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('cuota_retencion', sa.Numeric(precision=19, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['factura_id'], ['factura.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('linea_factura_iva', schema=None) as batch_op:
        batch_op.create_index('ix_linea_factura_factura', ['factura_id'], unique=False)

    op.create_table('liquidacion_impuesto_sociedades',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ejercicio_id', sa.Integer(), nullable=False),
    sa.Column('resultado_contable', sa.Numeric(precision=19, scale=2), nullable=False),
    sa.Column('ajustes_json', sa.String(length=12000), nullable=False),
    sa.Column('tipo_gravamen', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('retenciones_pagos_cuenta', sa.Numeric(precision=19, scale=2), nullable=False),
    sa.Column('base_imponible', sa.Numeric(precision=19, scale=2), nullable=True),
    sa.Column('cuota_integra', sa.Numeric(precision=19, scale=2), nullable=True),
    sa.Column('cuota_diferencial', sa.Numeric(precision=19, scale=2), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('asiento_id', sa.Integer(), nullable=True),
    sa.Column('creado_por_usuario_id', sa.Integer(), nullable=False),
    sa.Column('cerrado_por_usuario_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('cerrado_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['asiento_id'], ['asiento.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['cerrado_por_usuario_id'], ['usuario.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['creado_por_usuario_id'], ['usuario.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['ejercicio_id'], ['ejercicio.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ejercicio_id', name='uq_lis_ejercicio')
    )

    op.create_table('fichero_presentacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ejercicio_id', sa.Integer(), nullable=False),
    sa.Column('modelo', sa.String(length=3), nullable=False),
    sa.Column('periodo', sa.String(length=8), nullable=False),
    sa.Column('ruta', sa.String(length=255), nullable=False),
    sa.Column('hash_sha256', sa.String(length=64), nullable=False),
    sa.Column('generado_por_usuario_id', sa.Integer(), nullable=False),
    sa.Column('generado_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['ejercicio_id'], ['ejercicio.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['generado_por_usuario_id'], ['usuario.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ejercicio_id', 'modelo', 'periodo', name='uq_fichero_ejercicio_modelo_periodo')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('fichero_presentacion')
    op.drop_table('liquidacion_impuesto_sociedades')
    with op.batch_alter_table('linea_factura_iva', schema=None) as batch_op:
        batch_op.drop_index('ix_linea_factura_factura')
    op.drop_table('linea_factura_iva')
    with op.batch_alter_table('factura', schema=None) as batch_op:
        batch_op.drop_index('ix_factura_ejercicio_origen')
        batch_op.drop_index('ix_factura_ejercicio_fecha')
    op.drop_table('factura')