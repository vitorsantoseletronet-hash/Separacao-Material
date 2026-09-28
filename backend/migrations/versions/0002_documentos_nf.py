"""PDF da nota fiscal vinculado explicitamente à remessa."""
from alembic import op
import sqlalchemy as sa

revision = "0002_documentos_nf"
down_revision = "0001_api"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("api_documentos_nf",
        sa.Column("remessa_id", sa.String(36), sa.ForeignKey("api_remessas.id"), primary_key=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("api_documentos_nf")
