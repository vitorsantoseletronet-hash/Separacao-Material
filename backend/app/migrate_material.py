"""Importa snapshot da aba Envio da Material.xlsx; simula por padrão."""
import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from sqlalchemy import select
from .db import make_engine, session_factory
from .models import Projeto, Item, Remessa, RemessaItem, ImportacaoLegada
from .schemas import codigo_projeto
from .services import localidade


def text(value):
    return '' if value is None else str(value).strip()


def parse_date(value):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(text(value), fmt).date()
        except ValueError:
            pass
    return None


def import_snapshot(db, source):
    groups = defaultdict(list)
    for row in source['linhas']:
        groups[codigo_projeto(row['valores'][0])].append(row)
    report = {'projetos': 0, 'itens': 0, 'remessas': 0, 'revisar': 0, 'ja_importados': 0}
    for code, rows in groups.items():
        original = {'arquivo': source['arquivo'], 'aba': source['aba'], 'codigo': code, 'linhas': rows}
        digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if db.scalar(select(ImportacaoLegada.id).where(ImportacaoLegada.sha256 == digest)):
            report['ja_importados'] += 1
            continue
        if db.scalar(select(Projeto.id).where(Projeto.codigo == code)):
            raise ValueError(f'{code} já existe. Importação cancelada para não substituir ou duplicar materiais.')
        owners = list(dict.fromkeys(text(row['valores'][6]) for row in rows if row['valores'][6]))
        project = Projeto(codigo=code, arquivo='Material.xlsx — Envio', metodo='planilha', responsavel_implantacao=' / '.join(owners))
        db.add(project); db.flush()
        shipments = {}
        warnings = []
        for order, row in enumerate(rows):
            _, sent, destination, description, serial, size, owner, nf = row['valores']
            review = []
            match = re.match(r'^\s*(\d+)\s+(.+)$', text(description), re.S)
            qty = int(match[1]) if match and int(match[1]) > 0 else None
            desc = match[2].strip() if match else text(description)
            if qty is None: review.append('Quantidade não explícita na planilha')
            loc = localidade(db, text(destination))
            if not loc: review.append('Destino ausente')
            if not desc: review.append('Descrição ausente')
            color = row['cores'][3] or {}
            status = 'nao_separado'
            if color.get('pattern') == 'solid':
                if color.get('type') == 'theme' and color.get('value') == 6:
                    status = 'separado'
                elif color.get('value') == 'FFFF0000':
                    status = 'sem_estoque'
                elif color.get('value') == 'FFFFFF00':
                    status = 'outro_local'; review.append('Confirmar origem do item remanejado')
                elif not (color.get('type') == 'theme' and color.get('value') == 0):
                    review.append('Cor sem significado definido na legenda')
            sent_date = parse_date(sent)
            historic = bool(sent_date or text(nf))
            if historic:
                review.append('Conferir envio histórico antes de nova remessa')
            elif text(sent):
                review.append('Campo Envio sem data válida: ' + text(sent))
            notes = f"Material.xlsx / Envio / linha {row['linha']}. Código original: {row['valores'][0]}."
            if size: notes += f' Tamanho: {size}.'
            if sent: notes += f' Envio original: {sent}.'
            if nf: notes += f' NF original: {nf}.'
            item = Item(projeto_id=project.id, localidade_id=loc.id if loc else None, ordem=order,
                        descricao=desc, quantidade=qty, status=status, serial=text(serial),
                        responsavel=text(owner), observacoes=notes, revisao='; '.join(review))
            db.add(item); db.flush()
            if historic and loc:
                key = (loc.id, text(nf), text(sent))
                if key not in shipments:
                    shipment = Remessa(localidade_id=loc.id, status='legado_revisar', nf=text(nf),
                        observacoes=f'Importado de {code}, Material.xlsx. Data de envio original: {text(sent) or "não informada"}. Conferir quantidades e data de entrega à logística.')
                    db.add(shipment); db.flush(); shipments[key] = shipment
                if qty:
                    db.add(RemessaItem(remessa_id=shipments[key].id, item_id=item.id, quantidade=qty))
            if review: warnings.append(f"Linha {row['linha']}: " + '; '.join(review))
            report['itens'] += 1
            report['revisar'] += bool(review)
        db.add(ImportacaoLegada(projeto_id=project.id, sha256=digest,
            nome_arquivo='Material.xlsx / Envio', original=original, avisos=warnings))
        report['projetos'] += 1
        report['remessas'] += len(shipments)
    db.flush()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    source = json.loads(args.snapshot.read_text(encoding='utf-8'))
    with session_factory(make_engine())() as db:
        report = import_snapshot(db, source)
        if args.apply: db.commit()
        else: db.rollback()
    print(json.dumps({'gravado': args.apply, **report}, ensure_ascii=False))


if __name__ == '__main__':
    main()
