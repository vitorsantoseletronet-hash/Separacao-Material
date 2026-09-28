import { useMemo, useState } from 'react'
import { CalendarDays, FileCheck2, FileText, Search, Truck } from 'lucide-react'
import { request } from '../api'
import { localDate, shipmentLabels, type Shipment } from '../types'
import { AsyncForm, Empty, Modal } from '../components/UI'
export function Shipments({ shipments, reload, notify }: {shipments: Shipment[]; reload: () => Promise<void>; notify: (text: string) => void}) {
  const [upload, setUpload] = useState(false)
  const [search, setSearch] = useState(''), [status, setStatus] = useState(''), [action, setAction] = useState<{ r: Shipment; mode: 'nf' | 'date' | 'cancel' } | null>(null)
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return shipments.filter(r => (!status || r.status === status) && `${r.destino} ${r.nf} ${r.itens.map(i => i.codigo_projeto).join(' ')}`.toLowerCase().includes(term))
  }, [search, shipments, status])
  return <><div className="page-heading"><div><div className="eyebrow">EXPEDIÇÃO • CONTROLE DE ENVIO</div><h1>Remessas e notas fiscais</h1><p>Anexe o PDF da NF e vincule pelo número ao envio correspondente.</p></div><button className="button primary" onClick={() => setUpload(true)}><FileText size={17}/>Anexar NF em PDF</button></div><div className="shipment-toolbar"><div className="input-icon"><Search size={17}/><input aria-label="Buscar remessas" placeholder="Localidade, NF ou PS/PSC…" value={search} onChange={e => setSearch(e.target.value)}/></div><select aria-label="Situação da remessa" value={status} onChange={e => setStatus(e.target.value)}><option value="">Todas as situações</option>{Object.entries(shipmentLabels).map(([k,l]) => <option key={k} value={k}>{l}</option>)}</select></div>
    {!filtered.length ? <section className="panel"><Empty title="Nenhuma remessa encontrada">Na Separação, selecione os materiais de um destino e clique em Criar remessa.</Empty></section> : <div className="shipment-list">{filtered.map(r => <article className="panel shipment-card" key={r.id}><header><div className="destination-icon"><Truck size={21}/></div><div><h2>{r.destino}</h2><p>{r.itens.length} materiais · {new Set(r.itens.map(i => i.codigo_projeto)).size} projetos · saída: {r.origem_expedicao === 'LOCAL' ? 'Estoque local' : r.origem_expedicao}</p></div><span className={`shipment-status ${r.status}`}>{shipmentLabels[r.status]}</span></header><div className="shipment-meta"><span><FileText size={17}/>NF <strong>{r.nf || 'Não registrada'}</strong></span><span><CalendarDays size={17}/>Entrega à logística <strong>{r.data_entrega_logistica ? r.data_entrega_logistica.split('-').reverse().join('/') : 'Não registrada'}</strong></span></div>
      {r.nf_arquivo && <p><a className="button secondary" href={`/api/remessas/${r.id}/nf/pdf`} target="_blank" rel="noreferrer"><FileText size={16}/>Abrir NF em PDF</a></p>}
      {r.status === 'legado_revisar' && <p className="notice">Envio importado do controle antigo. As quantidades precisam ser conferidas antes de contabilizar este envio. O histórico original foi preservado.</p>}
      <details><summary>Materiais desta remessa</summary><div className="table-scroll"><table><thead><tr><th>Projeto</th><th>Material</th><th>Serial / tamanho</th><th>Quantidade</th></tr></thead><tbody>{r.itens.map(i => <tr key={i.item_id}><td><span className="project-tag">{i.codigo_projeto}</span></td><td>{i.descricao}</td><td>{i.serial || '—'}</td><td>{i.quantidade}</td></tr>)}</tbody></table></div></details>{r.observacoes && <p className="muted">{r.observacoes}</p>}
      {['rascunho','nf_solicitada','nf_registrada'].includes(r.status) && <footer><button className="button text-button" onClick={() => setAction({r, mode:'cancel'})}>Cancelar remessa</button><div><button className="button secondary" onClick={() => setAction({r, mode:'nf'})}><FileCheck2 size={16}/>{r.nf ? 'Editar número da NF' : 'Informar número da NF'}</button>{r.status === 'nf_registrada' && <button className="button primary" onClick={() => setAction({r, mode:'date'})}><Truck size={16}/>Entregar à logística</button>}</div></footer>}
    </article>)}</div>}
    {upload && <InvoiceUpload shipments={shipments} onClose={() => setUpload(false)} onSaved={async () => { await reload(); notify('PDF da NF vinculado ao envio.'); setUpload(false) }}/>}
    {action && <ShipmentAction key={`${action.r.id}-${action.mode}`} {...action} onClose={() => setAction(null)} onSaved={async () => { await reload(); notify('Remessa atualizada.'); setAction(null) }}/>}
  </>
}
function ShipmentAction({ r, mode, onClose, onSaved }: {r: Shipment; mode: 'nf'|'date'|'cancel'; onClose: () => void; onSaved: () => Promise<void>}) {
  const [nf, setNf] = useState(r.nf), [date, setDate] = useState(localDate())
  const titles = {nf: 'Informar número da NF', date: 'Entrega à logística', cancel: 'Cancelar remessa'}
  return <Modal title={titles[mode]} subtitle={r.destino} onClose={onClose}><AsyncForm label={mode === 'cancel' ? 'Confirmar cancelamento' : 'Salvar registro'} onCancel={onClose} onSubmit={async () => { if (mode === 'nf') await request(`/remessas/${r.id}/nf`, 'PUT', { nf }); else if (mode === 'date') await request(`/remessas/${r.id}/entregar-logistica`, 'POST', { data_entrega_logistica: date }); else await request(`/remessas/${r.id}/cancelar`, 'POST'); await onSaved() }}>
    {mode === 'nf' && <><p className="info-strip">A NF é emitida fora do sistema. Informe abaixo o número para controle desta remessa.</p><label>Número da NF<input required value={nf} onChange={e => setNf(e.target.value)} placeholder="Ex.: 000123"/></label></>}
    {mode === 'date' && <><p className="info-strip">Informe a data em que você deixou os materiais com a logística para envio.</p><label>Data de entrega à logística<input required type="date" max={localDate()} value={date} onChange={e => setDate(e.target.value)}/></label></>}

    {mode === 'cancel' && <p>Os materiais desta remessa voltarão a ficar disponíveis para um novo envio. O registro da remessa será mantido como cancelado.</p>}
  </AsyncForm></Modal>
}

function InvoiceUpload({ shipments, onClose, onSaved }: { shipments: Shipment[]; onClose: () => void; onSaved: () => Promise<void> }) {
  const [nf, setNf] = useState(''), [shipmentId, setShipmentId] = useState(''), [file, setFile] = useState<File | null>(null)
  const eligible = shipments.filter(r => !r.nf_arquivo && ['rascunho', 'nf_solicitada', 'nf_registrada', 'entregue_logistica'].includes(r.status) && (!r.nf || r.nf === nf.trim()))
  return <Modal title="Anexar NF em PDF" subtitle="Informe o número que aparece na nota e confira o envio antes de vincular." onClose={onClose}><AsyncForm label="Vincular PDF ao envio" onCancel={onClose} onSubmit={async () => {
    if (!file) throw new Error('Selecione o PDF da nota fiscal.')
    if (file.size > 30 * 1024 * 1024) throw new Error('O PDF deve ter no máximo 30 MB.')
    if (!eligible.some(r => r.id === shipmentId)) throw new Error('Selecione o envio correspondente à NF.')
    const body = new FormData(); body.append('nf', nf.trim()); body.append('arquivo', file)
    await request(`/remessas/${shipmentId}/nf/pdf`, 'POST', body); await onSaved()
  }}>
    <label>Número da NF<input required maxLength={100} value={nf} onChange={e => { setNf(e.target.value); setShipmentId('') }} placeholder="Ex.: 000123"/></label>
    <label>PDF da nota fiscal<input required type="file" accept=".pdf,application/pdf" onChange={e => setFile(e.target.files?.[0] ?? null)}/></label>
    <label>Envio correspondente<select required value={shipmentId} onChange={e => setShipmentId(e.target.value)}><option value="">Selecione o envio</option>{eligible.map(r => <option key={r.id} value={r.id}>{r.destino} · {r.origem_expedicao} · {r.itens.map(i => i.codigo_projeto).filter((v, i, a) => a.indexOf(v) === i).join(', ')} · NF {r.nf || 'não registrada'} · {r.id.slice(0, 8)}</option>)}</select></label>
    <p className="info-strip">São exibidos os envios com esse número de NF ou sem NF registrada. Confira também o destino e os projetos. O número é informado por você; não é extraído automaticamente do PDF.</p>
    {!eligible.length && <p className="notice">Nenhum envio disponível. Confira o número ou crie uma remessa na Separação.</p>}
  </AsyncForm></Modal>
}
