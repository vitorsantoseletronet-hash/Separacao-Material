import pytest
from sqlalchemy import select, func
from backend.app.migrate_material import import_snapshot
from backend.app.models import Item, Projeto, Remessa
from backend.app.schemas import codigo_projeto


def test_material_preserva_ano_revisao_e_idempotencia(factory):
    source={'arquivo':'Material.xlsx','aba':'Envio','linhas':[
        {'linha':2,'valores':['PSC 226-26 rev 1.1','2026-09-24 00:00:00','SITE A','02 Módulos','ABC','2m','João',123], 'cores':[None,None,None,{'type':'theme','value':6,'pattern':'solid'},None,None,None,None]},
        {'linha':3,'valores':['PSC 226-26 rev 1.1',None,'SITE A','DM4770',None,None,'João',None], 'cores':[None]*8}]}
    with factory() as db:
        report=import_snapshot(db,source)
        assert report['itens']==2 and report['remessas']==1
        db.commit()
    with factory() as db:
        assert import_snapshot(db,source)['ja_importados']==1
        items=db.scalars(select(Item).order_by(Item.ordem)).all()
        assert items[0].quantidade==2 and items[0].serial=='ABC'
        assert items[1].quantidade is None and items[1].revisao
        remessa=db.scalar(select(Remessa))
        assert remessa.status=='legado_revisar' and remessa.data_entrega_logistica is None
        assert remessa.nf=='123' and remessa.itens[0].quantidade==2
        assert db.scalar(select(func.count()).select_from(Projeto))==1
        source['linhas'][0]['valores'][3]='03 Módulos'
        with pytest.raises(ValueError,match='já existe'): import_snapshot(db,source)


def test_codigos_planilha():
    assert codigo_projeto('PSC 052/2025')=='PSC 52/2025'
    assert codigo_projeto('PSC 226-26 rev 1.1')=='PSC 226-26 REV 1.1'
    assert codigo_projeto('ps-00100')=='PS 100'
