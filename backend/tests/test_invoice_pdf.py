import io
from datetime import date
import pypdfium2 as pdfium
from test_api import project, shipment


def pdf_bytes():
    stream = io.BytesIO()
    with pdfium.PdfDocument.new() as pdf:
        page = pdf.new_page(300, 300)
        page.close()
        pdf.save(stream)
    return stream.getvalue()


def test_nf_pdf_persistencia_e_protecao(client):
    rid = shipment(client, project(client)).json()['id']
    url = f'/remessas/{rid}/nf/pdf'
    content = pdf_bytes()
    assert client.get(url).status_code == 404
    assert client.post(url, data={'nf': '000123'}, files={'arquivo': ('nf.pdf', b'invalido')}).status_code == 422
    result = client.post(url, data={'nf': '000123'}, files={'arquivo': ('nota.pdf', content)})
    assert result.status_code == 200, result.text
    assert result.json()['nf'] == '000123'
    assert result.json()['nf_arquivo'] == 'nota.pdf'
    assert result.json()['status'] == 'nf_registrada'
    downloaded = client.get(url)
    assert downloaded.content == content
    assert downloaded.headers['content-type'] == 'application/pdf'
    assert client.get('/remessas').json()[0]['nf_arquivo'] == 'nota.pdf'
    assert client.post(url, data={'nf': '000123'}, files={'arquivo': ('outra.pdf', content)}).status_code == 409
    assert client.put(f'/remessas/{rid}/nf', json={'nf': '999'}).status_code == 409


def test_nf_pdf_confere_numero_e_preserva_entrega(client):
    rid = shipment(client, project(client)).json()['id']
    client.put(f'/remessas/{rid}/nf', json={'nf': '123'})
    client.post(f'/remessas/{rid}/entregar-logistica', json={'data_entrega_logistica': str(date.today())})
    url = f'/remessas/{rid}/nf/pdf'
    assert client.post(url, data={'nf': '999'}, files={'arquivo': ('nf.pdf', pdf_bytes())}).status_code == 409
    result = client.post(url, data={'nf': '123'}, files={'arquivo': ('nf.pdf', pdf_bytes())})
    assert result.status_code == 200
    assert result.json()['status'] == 'entregue_logistica'


def test_nf_pdf_rejeita_cancelada(client):
    rid = shipment(client, project(client)).json()['id']
    client.post(f'/remessas/{rid}/cancelar')
    assert client.post(f'/remessas/{rid}/nf/pdf', data={'nf': '123'}, files={'arquivo': ('nf.pdf', pdf_bytes())}).status_code == 409
