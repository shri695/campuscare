import { useEffect, useMemo, useState } from 'react'
import { Routes, Route, NavLink, Link, Navigate, useNavigate, useLocation } from 'react-router-dom'
import {
  Activity, Bell, CalendarDays, Check, ChevronDown, Clock3, HeartPulse, Home,
  Hospital, LogOut, Menu, MessageCircle, Plus, Search, ShieldCheck, Stethoscope,
  UserRound, Users, X, ArrowRight, Sparkles, FileHeart, MapPin, Send, Trash2,
  CircleAlert, LayoutDashboard, Settings2, Mail, ClipboardList
} from 'lucide-react'
import { api, login as loginApi, register as registerApi } from './api'

const today = new Date().toISOString().slice(0, 10)
const money = value => `₹${Number(value || 0).toLocaleString('en-IN')}`

function App() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('mediconnect_user') || 'null') } catch { return null }
  })
  const [mobileOpen, setMobileOpen] = useState(false)
  const [toast, setToast] = useState('')
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(''), 3400)
    return () => clearTimeout(timer)
  }, [toast])

  const saveSession = (session) => {
    localStorage.setItem('mediconnect_token', session.token)
    localStorage.setItem('mediconnect_user', JSON.stringify(session.user))
    setUser(session.user)
  }
  const logout = () => {
    localStorage.removeItem('mediconnect_token')
    localStorage.removeItem('mediconnect_user')
    setUser(null)
    navigate('/login')
  }
  const notify = (message) => setToast(message)
  const isAuthPage = ['/login', '/register'].includes(location.pathname)

  return (
    <>
      {!user || isAuthPage ? (
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <AuthPage mode="login" onSuccess={saveSession} notify={notify} />} />
          <Route path="/register" element={user ? <Navigate to="/dashboard" replace /> : <AuthPage mode="register" onSuccess={saveSession} notify={notify} />} />
          <Route path="*" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} />
        </Routes>
      ) : (
        <div className="app-shell">
          <Sidebar user={user} mobileOpen={mobileOpen} close={() => setMobileOpen(false)} logout={logout} />
          <div className="main-shell">
            <Topbar user={user} onMenu={() => setMobileOpen(v => !v)} />
            <main className="page-content">
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={user.role === 'admin' ? <AdminPage notify={notify} /> : <DashboardPage user={user} notify={notify} />} />
                <Route path="/chat" element={<ChatPage notify={notify} />} />
                <Route path="/doctors" element={<DoctorsPage notify={notify} />} />
                <Route path="/appointments" element={<AppointmentsPage notify={notify} />} />
                <Route path="/records" element={<RecordsPage notify={notify} />} />
                <Route path="/hospitals" element={<HospitalsPage notify={notify} />} />
                <Route path="/profile" element={<ProfilePage user={user} setUser={setUser} notify={notify} />} />
                <Route path="/admin" element={user.role === 'admin' ? <AdminPage notify={notify} /> : <Navigate to="/dashboard" replace />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </main>
          </div>
          {toast && <div className="toast"><Check size={17}/>{toast}</div>}
        </div>
      )}
    </>
  )
}

function Sidebar({ user, mobileOpen, close, logout }) {
  const patientLinks = [
    [LayoutDashboard, 'Overview', '/dashboard'],
    [MessageCircle, 'AI Health Assistant', '/chat'],
    [Stethoscope, 'Find a Doctor', '/doctors'],
    [CalendarDays, 'Appointments', '/appointments'],
    [FileHeart, 'Health Records', '/records'],
    [Hospital, 'Nearby Hospitals', '/hospitals'],
  ]
  const adminLinks = [[LayoutDashboard, 'Admin Overview', '/admin'], [Stethoscope, 'Doctor Directory', '/doctors']]
  const links = user.role === 'admin' ? adminLinks : patientLinks
  return (
    <>
      {mobileOpen && <button className="mobile-scrim" onClick={close} aria-label="Close navigation"/>}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-row"><div className="brand-mark"><HeartPulse size={21}/></div><div className="brand-name">MediConnect<span>AI CARE PLATFORM</span></div><button className="icon-button sidebar-close" onClick={close}><X size={18}/></button></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav">{links.map(([Icon,label,path]) => <NavLink key={label} to={path} onClick={close} className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={18}/><span>{label}</span>{label==='AI Health Assistant' && <span className="new-tag">AI</span>}</NavLink>)}</nav>
        <div className="sidebar-bottom">
          <div className="help-card"><div className="help-icon"><ShieldCheck size={17}/></div><b>Your care, connected</b><p>One place for health guidance and appointment planning.</p><span>Privacy-first design</span></div>
          <NavLink to="/profile" onClick={close} className="profile-mini"><div className="avatar">{user.full_name?.[0]?.toUpperCase() || 'M'}</div><div className="profile-mini-text"><b>{user.full_name}</b><small>{user.role === 'admin' ? 'Administrator' : 'Patient account'}</small></div><button className="icon-button logout-button" onClick={(e)=>{e.preventDefault();logout()}} title="Log out"><LogOut size={16}/></button></NavLink>
        </div>
      </aside>
    </>
  )
}

function Topbar({ user, onMenu }) {
  return <header className="topbar"><button className="icon-button menu-button" onClick={onMenu}><Menu size={20}/></button><div className="breadcrumb">Workspace <span>/</span> <b>{user.role === 'admin' ? 'Administrator' : 'Patient portal'}</b></div><div className="topbar-right"><div className="secure-label"><ShieldCheck size={14}/> Secure session</div><button className="icon-button notification-button" title="Notifications"><Bell size={18}/><i/></button><div className="avatar small-avatar">{user.full_name?.[0]?.toUpperCase() || 'M'}</div></div></header>
}

function PageHeading({ eyebrow, title, description, right }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{right}</div>
}
function Card({ children, className = '' }) { return <section className={`panel ${className}`}>{children}</section> }
function StatCard({ icon: Icon, label, value, note, tone = 'mint' }) { return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={19}/></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div> }
function Empty({ title, text }) { return <div className="empty-state"><div className="empty-icon"><ClipboardList size={22}/></div><b>{title}</b><p>{text}</p></div> }
function Spinner() { return <span className="spinner"/> }

function AuthPage({ mode, onSuccess, notify }) {
  const [form, setForm] = useState({ full_name: '', email: '', password: '', consent: false })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const update = (key, value) => setForm(v => ({ ...v, [key]: value }))
  async function submit(e) {
    e.preventDefault(); setError(''); setBusy(true)
    try {
      const result = mode === 'login'
        ? await loginApi(form.email, form.password)
        : await registerApi(form.full_name, form.email, form.password, form.consent)
      onSuccess(result); notify(mode === 'login' ? 'Welcome back to MediConnect.' : 'Your patient account is ready.')
      navigate('/dashboard')
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <div className="auth-layout"><div className="auth-visual"><div className="auth-brand"><div className="brand-mark"><HeartPulse size={21}/></div>MediConnect<span>AI</span></div><div className="visual-content"><div className="visual-pill"><Sparkles size={15}/> INTELLIGENT HEALTHCARE</div><h1>Better access.<br/><em>More connected</em> care.</h1><p>Bring health guidance, doctor discovery and appointment management together in one thoughtful space.</p><div className="visual-points"><span><Check size={15}/> AI-powered general health information</span><span><Check size={15}/> Simple appointment planning</span><span><Check size={15}/> Personal health record space</span></div></div><div className="visual-foot">Built to support—not replace—professional healthcare.</div><div className="orb orb-one"/><div className="orb orb-two"/></div><div className="auth-form-side"><div className="auth-mobile-brand"><div className="brand-mark"><HeartPulse size={20}/></div>MediConnect<span>AI</span></div><div className="auth-form-wrap"><div className="form-intro"><div className="eyebrow">PATIENT PORTAL</div><h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2><p>{mode === 'login' ? 'Sign in to continue your healthcare journey.' : 'Get started with a connected healthcare experience.'}</p></div>{error && <div className="inline-error"><CircleAlert size={16}/>{error}</div>}<form onSubmit={submit} className="auth-form">{mode === 'register' && <label>Full name<input value={form.full_name} onChange={e=>update('full_name',e.target.value)} placeholder="Enter your full name" required/></label>}<label>Email address<input type="email" value={form.email} onChange={e=>update('email',e.target.value)} placeholder="name@example.com" required/></label><label>Password<input type="password" value={form.password} onChange={e=>update('password',e.target.value)} placeholder={mode==='register'?'At least 10 characters':'Enter your password'} minLength={mode==='register'?10:1} required/></label>{mode==='register' && <label className="consent-row"><input type="checkbox" checked={form.consent} onChange={e=>update('consent',e.target.checked)} required/><span>I consent to processing my account and health information for this educational demo. Chat messages may be sent to the configured AI provider.</span></label>}<button className="btn btn-primary auth-submit" disabled={busy}>{busy ? <Spinner/> : null}{mode==='login'?'Sign in to MediConnect':'Create patient account'}<ArrowRight size={16}/></button></form><div className="auth-switch">{mode==='login' ? <>New to MediConnect? <Link to="/register">Create an account</Link></> : <>Already have an account? <Link to="/login">Sign in</Link></>}</div><div className="auth-security"><ShieldCheck size={15}/> Your credentials are handled securely by the backend.</div></div></div></div>
}

function DashboardPage({ user, notify }) {
  const [data, setData] = useState(null)
  const [doctors, setDoctors] = useState([])
  const [busy, setBusy] = useState(true)
  useEffect(() => { Promise.all([api('/api/dashboard'),api('/api/doctors')]).then(([d,dr])=>{setData(d.summary);setDoctors(dr.doctors.slice(0,3))}).catch(e=>notify(e.message)).finally(()=>setBusy(false)) }, [])
  const next = data?.next_appointment
  return <>
    <PageHeading eyebrow="YOUR HEALTH SPACE" title={`Good morning, ${user.full_name.split(' ')[0]}`} description="A clearer view of your healthcare, all in one place." right={<Link className="btn btn-primary" to="/doctors"><Plus size={16}/> Book an appointment</Link>}/>
    {busy ? <div className="loading-panel"><Spinner/>Loading your dashboard…</div> : <>
      <div className="stat-grid"><StatCard icon={CalendarDays} label="Total appointments" value={data?.appointments_total ?? 0} note="Across your care history" tone="mint"/><StatCard icon={Clock3} label="Upcoming visits" value={data?.upcoming_appointments ?? 0} note="Confirmed appointments" tone="blue"/><StatCard icon={FileHeart} label="Health records" value={data?.records_total ?? 0} note="Personal entries saved" tone="violet"/><StatCard icon={Activity} label="Care profile" value="Active" note="Your account is ready" tone="gold"/></div>
      <div className="dashboard-grid"><Card className="next-visit-card"><div className="section-head"><div><div className="eyebrow">YOUR NEXT STEP</div><h3>Upcoming appointment</h3></div><span className="status-badge confirmed">Confirmed</span></div>{next ? <div className="visit-detail"><div className="doctor-avatar large">{(next.doctor?.name || next.doctor_name || 'Dr').replace('Dr. ','').split(' ').map(x=>x[0]).slice(0,2).join('')}</div><div className="visit-info"><b>{next.doctor?.name || next.doctor_name}</b><span>{next.doctor?.specialization || next.specialization}</span><small>{next.doctor?.hospital || next.hospital}</small></div><div className="visit-time"><b>{new Date(`${next.date}T00:00:00`).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})}</b><span>{next.time_slot}</span></div></div> : <Empty title="No upcoming visits" text="Find a doctor and book a convenient appointment."/>}<Link to="/appointments" className="text-link">View appointments <ArrowRight size={15}/></Link></Card><Card className="assistant-promo"><div className="assistant-bubble"><Sparkles size={22}/></div><div className="eyebrow">MEDICONNECT AI</div><h3>Questions about your health?</h3><p>Get clear, general health information and learn when to seek professional care.</p><Link to="/chat" className="btn btn-white">Ask the AI assistant <ArrowRight size={15}/></Link><small>Not a diagnosis or substitute for medical advice.</small></Card></div>
      <div className="lower-grid"><Card><div className="section-head"><div><div className="eyebrow">CARE NETWORK</div><h3>Suggested doctors</h3></div><Link to="/doctors" className="text-link">View all <ArrowRight size={15}/></Link></div><div className="doctor-mini-list">{doctors.map(d=><div className="doctor-mini" key={d.id}><div className="doctor-avatar">{d.name.replace('Dr. ','').split(' ').map(x=>x[0]).slice(0,2).join('')}</div><div className="doctor-mini-info"><b>{d.name}</b><span>{d.specialization}</span><small>{d.hospital}</small></div><span className="mini-fee">{money(d.fee)}</span></div>)}</div></Card><Card><div className="section-head"><div><div className="eyebrow">QUICK ACTIONS</div><h3>Manage your care</h3></div></div><div className="quick-links"><Link to="/records"><div className="quick-icon lavender"><FileHeart/></div><div><b>Add health record</b><small>Keep important notes together</small></div><ArrowRight size={16}/></Link><Link to="/hospitals"><div className="quick-icon peach"><MapPin/></div><div><b>Nearby hospitals</b><small>Explore healthcare locations</small></div><ArrowRight size={16}/></Link><Link to="/profile"><div className="quick-icon blue"><UserRound/></div><div><b>My profile</b><small>Review your account details</small></div><ArrowRight size={16}/></Link></div></Card></div>
    </>}
    <div className="safety-note"><ShieldCheck size={17}/><span><b>Your information matters.</b> This academic prototype is for demonstration with fictional data only. Do not enter real medical or personal information.</span></div>
  </>
}

function ChatPage({ notify }) {
  const [messages,setMessages]=useState([{role:'assistant',text:'Hello! I’m MediConnect AI. I can share general health information, explain common terms and help you think about when to speak with a healthcare professional. I cannot diagnose or prescribe. What would you like to understand today?'}])
  const [input,setInput]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [historyLoaded,setHistoryLoaded]=useState(false)
  useEffect(()=>{api('/api/chat/history').then(r=>{if(r.messages?.length)setMessages(r.messages.flatMap(m=>[{role:'user',text:m.query},{role:'assistant',text:m.response,emergency:!!m.emergency_flag}]))}).catch(()=>{}).finally(()=>setHistoryLoaded(true))},[])
  async function send(e){e?.preventDefault(); const message=input.trim();if(!message||busy)return;setMessages(v=>[...v,{role:'user',text:message}]);setInput('');setBusy(true);setError('');try{const result=await api('/api/chat',{method:'POST',body:JSON.stringify({message})});setMessages(v=>[...v,{role:'assistant',text:result.reply,emergency:result.emergency}])}catch(err){setError(err.message);notify(err.message)}finally{setBusy(false)}}
  return <><PageHeading eyebrow="AI HEALTH ASSISTANT" title="Ask MediConnect AI" description="A conversational starting point for general health information." right={<div className="ai-live-pill"><span/> AI service connection</div>}/><div className="chat-layout"><div className="chat-main panel"><div className="chat-topline"><div className="ai-avatar"><Sparkles size={19}/></div><div><b>MediConnect AI Assistant</b><small>General health information · Safety-aware responses</small></div><span className="online-dot">Available</span></div><div className="chat-messages">{messages.map((m,i)=><div className={`chat-message ${m.role}`} key={i}><div className={`chat-face ${m.role==='assistant'?'ai-face':''}`}>{m.role==='assistant'?<Sparkles size={15}/>:<UserRound size={15}/>}</div><div className={`bubble ${m.emergency?'emergency-bubble':''}`}>{m.emergency&&<b className="urgent-label"><CircleAlert size={15}/> Urgent-care notice</b>}{m.text}</div></div>)}{busy&&<div className="chat-message assistant"><div className="chat-face ai-face"><Sparkles size={15}/></div><div className="bubble typing"><i/><i/><i/></div></div>}<div className="chat-end"/></div><form className="chat-composer" onSubmit={send}><textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder="Ask a general health question…" maxLength={2000}/><button className="send-button" disabled={!input.trim()||busy}><Send size={18}/></button><small>Enter to send · Shift + Enter for a new line</small></form></div><aside className="chat-side"><Card><div className="chat-side-icon"><ShieldCheck size={19}/></div><h3>Safe by design</h3><p>Responses are designed for general education, not individual diagnosis or treatment.</p><ul><li>Emergency phrase checks</li><li>Professional-care reminders</li><li>AI key stays on the server</li></ul></Card><Card><div className="eyebrow">TRY ASKING</div><h3>Suggested topics</h3><div className="suggestion-list">{['What does a routine health check-up include?','How can I build a better sleep routine?','What questions should I ask a general physician?','How can I manage exam stress?'].map(s=><button key={s} onClick={()=>setInput(s)}>{s}<ArrowRight size={14}/></button>)}</div></Card></aside></div><div className="medical-disclaimer"><CircleAlert size={17}/><span><b>Important:</b> AI-generated content can be incomplete or incorrect. Do not use this assistant for emergencies, diagnosis, medication or dosage decisions. For urgent concerns, contact emergency services (112 in India) or visit the nearest emergency department.</span></div></>
}

function DoctorsPage({ notify }) {
  const navigate = useNavigate()
  const [doctors,setDoctors]=useState([]);const [query,setQuery]=useState('');const [specialization,setSpecialization]=useState('');const [busy,setBusy]=useState(true);const [booking,setBooking]=useState(null);const [form,setForm]=useState({date:today,time_slot:'10:30',reason:'General consultation'});const [saving,setSaving]=useState(false)
  const specializations=useMemo(()=>Array.from(new Set(doctors.map(d=>d.specialization))).sort(),[doctors])
  async function load(){setBusy(true);try{const r=await api(`/api/doctors?q=${encodeURIComponent(query)}&specialization=${encodeURIComponent(specialization)}`);setDoctors(r.doctors)}catch(e){notify(e.message)}finally{setBusy(false)}}
  useEffect(()=>{load()},[query,specialization])
  async function book(e){e.preventDefault();setSaving(true);try{const r=await api('/api/appointments',{method:'POST',body:JSON.stringify({...form,doctor_id:booking.id})});notify(r.message);setBooking(null);navigateToAppointments()}catch(e){notify(e.message)}finally{setSaving(false)}}
  const navigateToAppointments=()=>navigate('/appointments')
  return <><PageHeading eyebrow="YOUR CARE NETWORK" title="Find your doctor" description="Explore healthcare professionals and choose a consultation that suits you."/><div className="search-bar panel"><div className="search-input"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search doctor, clinic or city"/></div><select value={specialization} onChange={e=>setSpecialization(e.target.value)}><option value="">All specializations</option>{specializations.map(s=><option key={s}>{s}</option>)}</select><span className="results-count">{doctors.length} doctors</span></div>{busy?<div className="loading-panel"><Spinner/>Finding doctors…</div>:<div className="doctors-grid">{doctors.map(d=><div className="doctor-card panel" key={d.id}><div className="doctor-card-top"><div className="doctor-avatar jumbo">{d.name.replace('Dr. ','').split(' ').map(x=>x[0]).slice(0,2).join('')}</div><span className="verified"><Check size={13}/> Verified profile</span></div><h3>{d.name}</h3><div className="doctor-specialty">{d.specialization}</div><p>{d.bio}</p><div className="doctor-meta"><span><Hospital size={14}/>{d.hospital}</span><span><MapPin size={14}/>{d.city}</span><span><Clock3 size={14}/>{d.experience} years experience</span></div><div className="doctor-card-bottom"><div><small>Consultation fee</small><b>{money(d.fee)}</b></div><button className="btn btn-primary" onClick={()=>{setBooking(d);setForm({date:today,time_slot:'10:30',reason:'General consultation'})}}>Book visit <ArrowRight size={15}/></button></div></div>)}</div>}{!busy&&!doctors.length&&<Empty title="No doctors found" text="Try another name, location or specialization."/>}{booking&&<div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setBooking(null)}}><div className="modal panel"><div className="modal-header"><div><div className="eyebrow">BOOK A CONSULTATION</div><h2>{booking.name}</h2><p>{booking.specialization} · {booking.hospital}</p></div><button className="icon-button" onClick={()=>setBooking(null)}><X/></button></div><form onSubmit={book} className="modal-form"><label>Appointment date<input type="date" min={today} value={form.date} onChange={e=>setForm(v=>({...v,date:e.target.value}))} required/></label><label>Time slot<select value={form.time_slot} onChange={e=>setForm(v=>({...v,time_slot:e.target.value}))}>{['09:00','10:30','12:00','14:00','15:30'].map(t=><option key={t}>{t}</option>)}</select></label><label>Reason for visit<textarea value={form.reason} onChange={e=>setForm(v=>({...v,reason:e.target.value}))} minLength={5} maxLength={500} required/></label><div className="modal-summary"><span>Consultation fee</span><b>{money(booking.fee)}</b></div><button className="btn btn-primary full-width" disabled={saving}>{saving?<Spinner/>:null}Confirm appointment</button><small className="muted">Demo booking only. Confirmations are stored in the project database.</small></form></div></div>}</>
}

function AppointmentsPage({ notify }) {
  const [items,setItems]=useState([]);const [busy,setBusy]=useState(true)
  const refresh=()=>api('/api/appointments').then(r=>setItems(r.appointments)).catch(e=>notify(e.message)).finally(()=>setBusy(false))
  useEffect(()=>{refresh()},[])
  async function cancel(id){try{await api(`/api/appointments/${id}/cancel`,{method:'POST',body:JSON.stringify({})});notify('Appointment cancelled.');refresh()}catch(e){notify(e.message)}}
  return <><PageHeading eyebrow="APPOINTMENT MANAGEMENT" title="Your appointments" description="Keep track of your upcoming consultations and previous bookings." right={<Link className="btn btn-primary" to="/doctors"><Plus size={16}/> New appointment</Link>}/><Card><div className="section-head"><div><h3>Appointment history</h3><p className="muted">Appointments booked through MediConnect.</p></div><span className="count-pill">{items.length} total</span></div>{busy?<div className="loading-panel"><Spinner/>Loading appointments…</div>:items.length?<div className="table-wrap"><table><thead><tr><th>Doctor</th><th>Date & time</th><th>Hospital</th><th>Status</th><th/></tr></thead><tbody>{items.map(a=><tr key={a.id}><td><b>{a.doctor?.name || a.doctor_name}</b><small>{a.doctor?.specialization || a.specialization}</small></td><td>{new Date(`${a.date}T00:00:00`).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})}<small>{a.time_slot}</small></td><td>{a.doctor?.hospital || a.hospital}</td><td><span className={`status-badge ${a.status}`}>{a.status}</span></td><td>{a.status==='confirmed'&&<button className="btn btn-soft-danger" onClick={()=>cancel(a.id)}>Cancel</button>}</td></tr>)}</tbody></table></div>:<Empty title="No appointments yet" text="Find a doctor to book your first consultation."/>}</Card></>
}

function RecordsPage({ notify }) {
  const [items,setItems]=useState([]);const [form,setForm]=useState({record_type:'General note',value:'',notes:'',recorded_on:today});const [busy,setBusy]=useState(true);const [saving,setSaving]=useState(false)
  const refresh=()=>api('/api/health-records').then(r=>setItems(r.records)).catch(e=>notify(e.message)).finally(()=>setBusy(false))
  useEffect(()=>{refresh()},[])
  async function save(e){e.preventDefault();setSaving(true);try{await api('/api/health-records',{method:'POST',body:JSON.stringify(form)});notify('Health record saved.');setForm(v=>({...v,value:'',notes:''}));refresh()}catch(e){notify(e.message)}finally{setSaving(false)}}
  async function remove(id){try{await api(`/api/health-records/${id}`,{method:'DELETE'});notify('Record deleted.');refresh()}catch(e){notify(e.message)}}
  return <><PageHeading eyebrow="PERSONAL HEALTH SPACE" title="Health records" description="Organize basic health notes and important information in one place."/><div className="records-layout"><Card><div className="eyebrow">NEW ENTRY</div><h3>Add a health record</h3><form className="stack-form" onSubmit={save}><label>Record type<select value={form.record_type} onChange={e=>setForm(v=>({...v,record_type:e.target.value}))}>{['General note','Allergy','Blood pressure','Weight','Height','Medication note','Visit summary','Other'].map(x=><option key={x}>{x}</option>)}</select></label><label>Value / observation<input value={form.value} onChange={e=>setForm(v=>({...v,value:e.target.value}))} placeholder="e.g. Seasonal pollen allergy" required/></label><label>Date recorded<input type="date" value={form.recorded_on} onChange={e=>setForm(v=>({...v,recorded_on:e.target.value}))} required/></label><label>Additional notes<textarea value={form.notes} onChange={e=>setForm(v=>({...v,notes:e.target.value}))} maxLength={500} placeholder="Optional notes"/></label><button className="btn btn-primary" disabled={saving}>{saving?<Spinner/>:null}<Plus size={16}/> Save record</button></form><div className="records-warning"><ShieldCheck size={16}/> Use fictional data in this academic prototype. Avoid entering real medical details.</div></Card><Card><div className="section-head"><div><div className="eyebrow">YOUR HISTORY</div><h3>Saved records</h3></div><span className="count-pill">{items.length}</span></div>{busy?<div className="loading-panel"><Spinner/>Loading records…</div>:items.length?<div className="record-list">{items.map(r=><div className="record-item" key={r.id}><div className="record-symbol"><FileHeart size={17}/></div><div className="record-content"><b>{r.record_type}</b><span>{r.value}</span><small>{r.recorded_on}{r.notes?` · ${r.notes}`:''}</small></div><button className="icon-button delete-button" onClick={()=>remove(r.id)} title="Delete record"><Trash2 size={16}/></button></div>)}</div>:<Empty title="No records saved" text="Add a first entry to build your personal health history."/>}</Card></div></>
}

function HospitalsPage({ notify }) {
  const [location,setLocation]=useState('Bengaluru');const [results,setResults]=useState([]);const [mapsUrl,setMapsUrl]=useState('');const [message,setMessage]=useState('');const [busy,setBusy]=useState(false)
  async function search(e){e.preventDefault();setBusy(true);setMessage('');try{const r=await api(`/api/hospitals/nearby?location=${encodeURIComponent(location)}`);setResults(r.hospitals||[]);setMapsUrl(r.maps_search_url||'');setMessage(r.message||'')}catch(e){notify(e.message)}finally{setBusy(false)}}
  useEffect(()=>{search({preventDefault(){}})},[])
  return <><PageHeading eyebrow="LOCAL CARE DISCOVERY" title="Nearby hospitals" description="Explore healthcare facilities around a location. Always call emergency services for urgent care."/><Card><form className="hospital-search" onSubmit={search}><div className="search-input"><MapPin size={17}/><input value={location} onChange={e=>setLocation(e.target.value)} placeholder="Enter a city or area"/></div><button className="btn btn-primary" disabled={busy}>{busy?<Spinner/>:<Search size={16}/>} Search hospitals</button></form>{message&&<div className="info-banner"><CircleAlert size={16}/>{message}</div>}{results.length?<div className="hospital-list">{results.map((h,i)=><div className="hospital-item" key={h.id||i}><div className="hospital-icon"><Hospital size={19}/></div><div><b>{h.displayName?.text||h.name||'Hospital'}</b><small>{h.formattedAddress||h.vicinity||''}</small></div>{h.googleMapsUri&&<a className="text-link" href={h.googleMapsUri} target="_blank" rel="noreferrer">Open map <ArrowRight size={14}/></a>}</div>)}</div>:<div className="maps-empty"><div className="maps-illustration"><MapPin size={30}/></div><h3>Find care around you</h3><p>{mapsUrl?'Use Google Maps to view nearby hospitals and clinics.':'Add a Google Maps Platform key to enable live place results; a maps search link is available meanwhile.'}</p>{mapsUrl&&<a className="btn btn-primary" href={mapsUrl} target="_blank" rel="noreferrer">Open Google Maps <ArrowRight size={15}/></a>}</div>}</Card><div className="safety-note"><CircleAlert size={16}/><span>Nearby listings are informational and may not reflect live availability, emergency capability or current operating status. Contact the facility before travelling.</span></div></>
}

function ProfilePage({ user, setUser, notify }) {
  const [name,setName]=useState(user.full_name);const [phone,setPhone]=useState('');const [busy,setBusy]=useState(false)
  useEffect(()=>{api('/api/profile').then(r=>setPhone(r.profile.phone||'')).catch(()=>{})},[])
  async function save(e){e.preventDefault();setBusy(true);try{await api('/api/profile',{method:'PUT',body:JSON.stringify({full_name:name,phone})});const next={...user,full_name:name};setUser(next);localStorage.setItem('mediconnect_user',JSON.stringify(next));notify('Profile updated.')}catch(e){notify(e.message)}finally{setBusy(false)}}
  return <><PageHeading eyebrow="ACCOUNT SETTINGS" title="Your profile" description="Review and update your basic account information."/><div className="profile-layout"><Card><div className="profile-hero"><div className="avatar profile-avatar">{user.full_name?.[0]?.toUpperCase()}</div><div><h3>{user.full_name}</h3><p>{user.role==='admin'?'Administrator':'Patient account'} · MediConnect AI</p></div><span className="verified"><ShieldCheck size={14}/> Secure account</span></div><form className="stack-form profile-form" onSubmit={save}><label>Full name<input value={name} onChange={e=>setName(e.target.value)} required minLength={2}/></label><label>Email address<input value={user.email} disabled/></label><label>Phone number (optional)<input value={phone} onChange={e=>setPhone(e.target.value)} placeholder="Add a contact number"/></label><button className="btn btn-primary" disabled={busy}>{busy?<Spinner/>:null}Save changes</button></form></Card><Card className="privacy-card"><div className="privacy-icon"><ShieldCheck size={22}/></div><h3>Privacy & consent</h3><p>Your account includes a consent record for this educational demonstration.</p><div className="privacy-point"><Check size={15}/> Passwords are hashed by the backend</div><div className="privacy-point"><Check size={15}/> AI provider key is server-side only</div><div className="privacy-point"><Check size={15}/> Account data is scoped to your user ID</div><small>For a real healthcare deployment, additional legal, security and clinical review is required.</small></Card></div></>
}

function AdminPage({ notify }) {
  const [data,setData]=useState(null);const [busy,setBusy]=useState(true);const [doctor,setDoctor]=useState({name:'',specialization:'General Physician',hospital:'',city:'Bengaluru',experience:0,fee:400,hours:'By appointment',bio:''});const [saving,setSaving]=useState(false)
  const refresh=()=>api('/api/admin/stats').then(setData).catch(e=>notify(e.message)).finally(()=>setBusy(false))
  useEffect(()=>{refresh()},[])
  async function cancel(id){try{await api(`/api/admin/appointments/${id}`,{method:'PATCH',body:JSON.stringify({status:'cancelled'})});notify('Appointment cancelled.');refresh()}catch(e){notify(e.message)}}
  async function addDoctor(e){e.preventDefault();setSaving(true);try{await api('/api/admin/doctors',{method:'POST',body:JSON.stringify(doctor)});notify('Doctor added.');setDoctor({name:'',specialization:'General Physician',hospital:'',city:'Bengaluru',experience:0,fee:400,hours:'By appointment',bio:''});refresh()}catch(e){notify(e.message)}finally{setSaving(false)}}
  return <><PageHeading eyebrow="ADMINISTRATION" title="Care operations" description="Monitor the platform and manage healthcare resources."/><div className="stat-grid four"><StatCard icon={Users} label="Patients" value={data?.stats?.patients??'—'} note="Registered accounts"/><StatCard icon={Stethoscope} label="Doctors" value={data?.stats?.doctors??'—'} note="Care professionals" tone="blue"/><StatCard icon={CalendarDays} label="Appointments" value={data?.stats?.appointments??'—'} note="All time" tone="violet"/><StatCard icon={Activity} label="Active visits" value={data?.stats?.active_appointments??'—'} note="Confirmed bookings" tone="gold"/></div>{busy?<div className="loading-panel"><Spinner/>Loading administration data…</div>:<div className="admin-grid"><Card><div className="section-head"><div><div className="eyebrow">BOOKING OVERSIGHT</div><h3>Recent appointments</h3></div><span className="count-pill">{data.appointments.length}</span></div>{data.appointments.length?<div className="admin-list">{data.appointments.map(a=><div className="admin-row" key={a.id}><div className="doctor-avatar">{(a.patient?.full_name||a.patient_name||'P')[0]}</div><div className="admin-row-info"><b>{a.patient?.full_name||a.patient_name}</b><small>{a.doctor?.name||a.doctor_name} · {a.date} · {a.time_slot}</small></div><span className={`status-badge ${a.status}`}>{a.status}</span>{a.status==='confirmed'&&<button className="icon-button delete-button" onClick={()=>cancel(a.id)} title="Cancel appointment"><X size={16}/></button>}</div>)}</div>:<Empty title="No appointment activity" text="Patient bookings will appear here."/>}</Card><Card><div className="eyebrow">CARE DIRECTORY</div><h3>Add a doctor</h3><form className="stack-form" onSubmit={addDoctor}><label>Doctor name<input value={doctor.name} onChange={e=>setDoctor(v=>({...v,name:e.target.value}))} required/></label><label>Specialization<input value={doctor.specialization} onChange={e=>setDoctor(v=>({...v,specialization:e.target.value}))} required/></label><label>Hospital / clinic<input value={doctor.hospital} onChange={e=>setDoctor(v=>({...v,hospital:e.target.value}))} required/></label><label>City<input value={doctor.city} onChange={e=>setDoctor(v=>({...v,city:e.target.value}))} required/></label><div className="form-pair"><label>Experience (years)<input type="number" min="0" value={doctor.experience} onChange={e=>setDoctor(v=>({...v,experience:e.target.value}))}/></label><label>Fee (₹)<input type="number" min="0" value={doctor.fee} onChange={e=>setDoctor(v=>({...v,fee:e.target.value}))}/></label></div><label>Consultation hours<input value={doctor.hours} onChange={e=>setDoctor(v=>({...v,hours:e.target.value}))}/></label><button className="btn btn-primary" disabled={saving}>{saving?<Spinner/>:null}<Plus size={16}/> Add doctor</button></form></Card><Card className="patients-card"><div className="eyebrow">REGISTERED USERS</div><h3>Patient accounts</h3>{data.patients.length?data.patients.slice(0,8).map(p=><div className="admin-row" key={p.id}><div className="avatar tiny-avatar">{p.full_name?.[0]}</div><div className="admin-row-info"><b>{p.full_name}</b><small>{p.email}</small></div><span className={`status-badge ${p.is_active?'confirmed':'cancelled'}`}>{p.is_active?'Active':'Inactive'}</span><button className="btn btn-soft-danger" onClick={async()=>{try{await api(`/api/admin/users/${p.id}`,{method:'PATCH',body:JSON.stringify({is_active:!p.is_active})});notify('Patient account updated.');refresh()}catch(e){notify(e.message)}}}>{p.is_active?'Deactivate':'Activate'}</button></div>):<Empty title="No patient accounts" text="New patient registrations will appear here."/>}</Card></div>}</>
}

export default App
