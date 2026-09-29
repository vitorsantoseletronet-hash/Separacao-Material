from datetime import date
from enum import Enum
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator


def texto_chave(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).upper()


def codigo_projeto(value: str) -> str:
    match = re.fullmatch(r"(PSC|PS)[\s:_/#.\-]*(\d{1,12})(?:([/-])(\d{2,4}))?(?:\s+rev\s*(\d+(?:\.\d+)*))?", value.strip(), re.I)
    if not match:
        raise ValueError("Informe o código PS ou PSC seguido do número, por exemplo PSC 2103.")
    suffix = f"{match[3]}{match[4]}" if match[3] else ""
    revision = f" REV {match[5]}" if match[5] else ""
    result = f"{match[1].upper()} {int(match[2])}{suffix}{revision}"
    if len(result) > 40:
        raise ValueError("Código do projeto excede 40 caracteres.")
    return result


class StatusItem(str, Enum):
    nao_separado = "nao_separado"
    separado = "separado"
    outro_local = "outro_local"
    sem_estoque = "sem_estoque"


CORES = {"nao_separado": "branco", "separado": "verde", "outro_local": "amarelo", "sem_estoque": "vermelho"}


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ItemEntrada(Entrada):
    destino: str = Field(min_length=1, max_length=250)
    descricao: str = Field(min_length=1, max_length=4000)
    quantidade: int = Field(gt=0, strict=True)
    status: StatusItem = StatusItem.nao_separado
    local_origem: str = Field(default="", max_length=250)
    tipo: str = ""
    serial: str = ""
    origem: str = ""
    responsavel: str = ""
    acao: str = ""
    observacoes: str = ""


class ProjetoEntrada(Entrada):
    codigo: str
    arquivo: str = ""
    paginas: int = Field(default=0, ge=0)
    metodo: str = Field(default="manual", max_length=40)
    projetista: str = ""
    responsavel_implantacao: str = ""
    itens: list[ItemEntrada] = Field(default_factory=list, max_length=10000)
    _codigo = field_validator("codigo")(codigo_projeto)


class ProjetoEdicao(Entrada):
    projetista: str
    responsavel_implantacao: str


class Selecionado(Entrada):
    item_id: str
    quantidade: int = Field(gt=0, strict=True)


class RemessaEntrada(Entrada):
    localidade_id: str
    origem_expedicao: str = Field(default="LOCAL", min_length=1, max_length=250)
    itens: list[Selecionado] = Field(min_length=1, max_length=10000)
    observacoes: str = ""


class NFEntrada(Entrada):
    nf: str = Field(min_length=1, max_length=100)


class EntregaEntrada(Entrada):
    data_entrega_logistica: date


class ReconciliacaoEntrada(Entrada):
    nf: str = Field(min_length=1, max_length=100)
    data_entrega_logistica: date | None = None
    itens: list[Selecionado] = Field(min_length=1, max_length=10000)
