import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  ArrowRight,
  BarChart3,
  Bell,
  BookOpen,
  BrainCircuit,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  Compass,
  Crosshair,
  Flame,
  Focus,
  Gauge,
  Goal,
  Heart,
  Home,
  LayoutDashboard,
  ListTodo,
  Lock,
  Menu,
  MessageCircle,
  Moon,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Save,
  Search,
  Settings,
  Sparkles,
  Sun,
  Target,
  TimerReset,
  TrendingUp,
  UserCircle2,
  Wallet,
  X,
  Zap
} from 'lucide-react';
import './styles.css';

const STORAGE_KEY = 'nexora-state-v1';

const defaultState = {
  profile: { name: 'Juan Diego', email: 'juan@nexora.local', onboarded: true },
  theme: 'dark',
  activeTab: 'dashboard',
  tasks: [
    { id: 1, title: 'Repasar integrales por sustitución', category: 'Estudio', due: 'Hoy', done: false, priority: 'high', minutes: 45, scheduled: '6:00 PM' },
    { id: 2, title: 'Avanzar módulo de autenticación', category: 'Proyecto', due: 'Hoy', done: false, priority: 'medium', minutes: 60, scheduled: '7:00 PM' },
    { id: 3, title: 'Registrar gastos de la semana', category: 'Dinero', due: 'Mañana', done: true, priority: 'low', minutes: 15, scheduled: '' },
    { id: 4, title: '30 min de entrenamiento', category: 'Hábitos', due: 'Hoy', done: false, priority: 'medium', minutes: 30, scheduled: '8:15 PM' }
  ],
  goals: [
    { id: 1, title: 'Lanzar mi primer MVP', subtitle: 'Producto digital', progress: 68, color: 'violet' },
    { id: 2, title: 'Ahorrar $500.000', subtitle: 'Finanzas', progress: 42, color: 'cyan' },
    { id: 3, title: 'Subir mi promedio', subtitle: 'Universidad', progress: 81, color: 'amber' }
  ],
  finance: {
    balance: 1840000,
    income: 2550000,
    expenses: 710000,
    expensesHistory: [120000, 90000, 155000, 88000, 62000, 74000, 121000]
  },
  study: {
    streak: 12,
    weeklyMinutes: 310,
    subjects: [
      { name: 'Cálculo', value: 84, sessions: 8 },
      { name: 'Programación', value: 71, sessions: 6 },
      { name: 'Bases de datos', value: 58, sessions: 4 }
    ]
  },
  habits: [
    { id: 1, title: 'Entrenar', streak: 6, active: true },
    { id: 2, title: 'Beber agua', streak: 12, active: true },
    { id: 3, title: 'Dormir antes de las 11 PM', streak: 4, active: false }
  ],
  dailyPlan: { organizedAt: 'Hoy · 5:45 PM', energy: 'Media', focus: 'Terminar lo importante sin saturarte' },
  circle: [
    { id: 1, name: 'Mamá', tag: 'Familia', note: 'Llamarla esta noche', online: true },
    { id: 2, name: 'Papá', tag: 'Familia', note: 'Cumpleaños · domingo', online: false },
    { id: 3, name: 'Sofi', tag: 'Amigos', note: 'Proyecto compartido', online: true }
  ]
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...defaultState, ...JSON.parse(raw) } : defaultState;
  } catch {
    return defaultState;
  }
}

function currency(value) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);
}

function todayLabel() {
  return new Intl.DateTimeFormat('es-CO', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
}

function Sparkline({ values }) {
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const width = 340;
  const height = 110;
  const points = values.map((v, i) => {
    const x = (i / Math.max(values.length - 1, 1)) * width;
    const y = height - ((v - min) / Math.max(max - min, 1)) * (height - 14) - 7;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="sparkline" role="img" aria-label="Histórico">
      <defs>
        <linearGradient id="sparkFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#8b5cf6" stopOpacity=".28" />
          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="1" points={`0,100 340,100`} />
      <polygon fill="url(#sparkFill)" points={`0,110 ${points} 340,110`} />
      <polyline fill="none" stroke="#a78bfa" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  );
}

function Ring({ value, label, icon: Icon, tone = 'violet' }) {
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (value / 100) * circumference;
  return (
    <div className={`ring-wrap ${tone}`}>
      <svg viewBox="0 0 110 110" className="ring">
        <circle cx="55" cy="55" r="45" className="ring-track" />
        <circle cx="55" cy="55" r="45" className="ring-value" strokeDasharray={circumference} strokeDashoffset={offset} />
      </svg>
      <div className="ring-center"><Icon size={18}/><strong>{value}%</strong><span>{label}</span></div>
    </div>
  );
}

function App() {
  const [state, setState] = useState(loadState);
  const [splash, setSplash] = useState(true);
  const [mobileNav, setMobileNav] = useState(false);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');
  const [assistantOpen, setAssistantOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  useEffect(() => {
    const timer = setTimeout(() => setSplash(false), 1650);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = state.theme;
  }, [state.theme]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 2600);
    return () => clearTimeout(t);
  }, [toast]);

  const taskProgress = useMemo(() => {
    const done = state.tasks.filter(t => t.done).length;
    return state.tasks.length ? Math.round((done / state.tasks.length) * 100) : 0;
  }, [state.tasks]);

  const navigate = (tab) => {
    setState(s => ({ ...s, activeTab: tab }));
    setMobileNav(false);
  };

  const toggleTask = (id) => {
    setState(s => ({ ...s, tasks: s.tasks.map(t => t.id === id ? { ...t, done: !t.done } : t) }));
  };

  const addTask = (title, category = 'Personal') => {
    if (!title.trim()) return;
    setState(s => ({ ...s, tasks: [{ id: Date.now(), title, category, due: 'Hoy', done: false, priority: 'medium' }, ...s.tasks] }));
    setModal(null);
    setToast('Tarea creada en tu flujo.');
  };

  const organizeDay = () => {
    setState(s => {
      const priorityWeight = { high: 0, medium: 1, low: 2 };
      const pending = s.tasks.filter(t => !t.done).sort((a,b) => (priorityWeight[a.priority] ?? 1) - (priorityWeight[b.priority] ?? 1));
      const starts = ['5:30 PM','6:20 PM','7:35 PM','8:20 PM','9:00 PM','9:40 PM'];
      const organized = s.tasks.map(task => {
        const idx = pending.findIndex(t => t.id === task.id);
        if (idx < 0) return task;
        return { ...task, due: 'Hoy', scheduled: starts[Math.min(idx, starts.length-1)] };
      });
      return { ...s, tasks: organized, dailyPlan: { organizedAt: 'Ahora', energy: 'Media', focus: 'Priorizar lo importante y dejar espacio para descansar' } };
    });
    setToast('NEXORA reorganizó tu día por prioridad y tiempo disponible.');
  };

  const addGoal = (title, subtitle) => {
    if (!title.trim()) return;
    setState(s => ({ ...s, goals: [{ id: Date.now(), title, subtitle: subtitle || 'Meta personal', progress: 0, color: 'violet' }, ...s.goals] }));
    setModal(null);
    setToast('Nueva meta añadida.');
  };

  const updateName = (name) => setState(s => ({ ...s, profile: { ...s.profile, name } }));

  if (splash) return <Splash />;

  return (
    <div className="app-shell">
      <Background />
      <header className="mobile-header">
        <button className="icon-btn" onClick={() => setMobileNav(true)} aria-label="Abrir menú"><Menu size={20}/></button>
        <Logo compact />
        <button className="icon-btn" onClick={() => setAssistantOpen(true)} aria-label="Abrir asistente"><Sparkles size={20}/></button>
      </header>

      <div className="layout">
        <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
          <div className="sidebar-top">
            <Logo />
            <button className="close-mobile" onClick={() => setMobileNav(false)}><X size={20}/></button>
            <div className="identity-chip">
              <div className="avatar">JD</div>
              <div><strong>{state.profile.name}</strong><span>Personal OS · Prototipo</span></div>
              <button className="mini-more"><MoreHorizontal size={18}/></button>
            </div>
          </div>
          <nav className="nav">
            <p className="nav-label">WORKSPACE</p>
            <NavItem icon={LayoutDashboard} text="Visión general" active={state.activeTab === 'dashboard'} onClick={() => navigate('dashboard')} />
            <NavItem icon={Target} text="Metas" active={state.activeTab === 'goals'} onClick={() => navigate('goals')} />
            <NavItem icon={ListTodo} text="Tareas" active={state.activeTab === 'tasks'} badge={state.tasks.filter(t=>!t.done).length} onClick={() => navigate('tasks')} />
            <NavItem icon={BookOpen} text="Estudio" active={state.activeTab === 'study'} onClick={() => navigate('study')} />
            <NavItem icon={Wallet} text="Dinero" active={state.activeTab === 'money'} onClick={() => navigate('money')} />
            <NavItem icon={Focus} text="Enfoque" active={state.activeTab === 'focus'} onClick={() => navigate('focus')} />
            <NavItem icon={Heart} text="Círculo" active={state.activeTab === 'circle'} onClick={() => navigate('circle')} />
            <p className="nav-label bottom-label">SYSTEM</p>
            <NavItem icon={Settings} text="Ajustes" active={state.activeTab === 'settings'} onClick={() => navigate('settings')} />
          </nav>
          <div className="sidebar-bottom">
            <button className="assistant-launch" onClick={() => setAssistantOpen(true)}>
              <span className="ai-orb"><Sparkles size={18}/></span>
              <span><strong>NEXORA AI</strong><small>Planifica tu siguiente movimiento</small></span>
              <ArrowRight size={17}/>
            </button>
            <p>v1.0 · Life OS</p>
          </div>
        </aside>

        <main className="main">
          <Topbar state={state} onAssistant={() => setAssistantOpen(true)} />
          <AnimatePresence mode="wait">
            <motion.div
              key={state.activeTab}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: .24 }}
              className="page"
            >
              {state.activeTab === 'dashboard' && <Dashboard state={state} taskProgress={taskProgress} navigate={navigate} toggleTask={toggleTask} setModal={setModal} organizeDay={organizeDay} />}
              {state.activeTab === 'goals' && <Goals state={state} setState={setState} setModal={setModal} />}
              {state.activeTab === 'tasks' && <Tasks state={state} toggleTask={toggleTask} addTask={addTask} />}
              {state.activeTab === 'study' && <Study state={state} setToast={setToast} />}
              {state.activeTab === 'money' && <Money state={state} />}
              {state.activeTab === 'focus' && <FocusPage setToast={setToast} />}
              {state.activeTab === 'circle' && <Circle state={state} setState={setState} setToast={setToast} />}
              {state.activeTab === 'settings' && <SettingsPage state={state} setState={setState} updateName={updateName} setToast={setToast} />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <AnimatePresence>{toast && <Toast text={toast} />}</AnimatePresence>
      <AnimatePresence>{modal && <Modal type={modal} onClose={() => setModal(null)} onAddTask={addTask} onAddGoal={addGoal} />}</AnimatePresence>
      <AnimatePresence>{assistantOpen && <Assistant onClose={() => setAssistantOpen(false)} addTask={addTask} navigate={navigate} setToast={setToast} organizeDay={organizeDay} /></AnimatePresence>
    </div>
  );
}

function Splash() {
  return (
    <motion.div className="splash" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.div className="splash-orbit orbit-one" animate={{ rotate: 360 }} transition={{ duration: 6, repeat: Infinity, ease: 'linear' }} />
      <motion.div className="splash-orbit orbit-two" animate={{ rotate: -360 }} transition={{ duration: 8, repeat: Infinity, ease: 'linear' }} />
      <motion.div initial={{ scale: .7, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: .8 }} className="splash-logo">N<span>×</span>RA</motion.div>
      <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .45 }} >TU SIGUIENTE MOVIMIENTO EMPIEZA AQUÍ</motion.p>
      <motion.div className="splash-line" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: .65, duration: .8 }} />
    </motion.div>
  );
}

function Background() {
  return <div className="ambient" aria-hidden="true"><div className="blob b1"/><div className="blob b2"/><div className="grid-lines"/></div>;
}

function Logo({ compact=false }) {
  return <div className={`logo ${compact ? 'compact' : ''}`}><span className="logo-mark"><span>N</span><i>×</i><span>R</span></span>{!compact && <span className="logo-word">NEXORA<small>PERSONAL LIFE OS</small></span>}</div>;
}

function Topbar({ state, onAssistant }) {
  return <div className="topbar">
    <div className="crumb"><span>Workspace</span><ChevronRight size={14}/><strong>{state.activeTab === 'dashboard' ? 'Visión general' : state.activeTab[0].toUpperCase()+state.activeTab.slice(1)}</strong></div>
    <div className="top-actions">
      <div className="search-pill"><Search size={16}/><span>Buscar</span><kbd>⌘ K</kbd></div>
      <button className="icon-btn"><Bell size={18}/><span className="notif-dot"/></button>
      <button className="ai-top" onClick={onAssistant}><Sparkles size={17}/> Pregunta a NEXORA</button>
    </div>
  </div>;
}

function NavItem({ icon: Icon, text, active, onClick, badge }) {
  return <button className={`nav-item ${active ? 'active' : ''}`} onClick={onClick}><Icon size={18}/><span>{text}</span>{badge ? <em>{badge}</em> : null}</button>;
}

function Dashboard({ state, taskProgress, navigate, toggleTask, setModal, organizeDay }) {
  const greeting = new Date().getHours() < 12 ? 'Buenos días' : new Date().getHours() < 19 ? 'Buenas tardes' : 'Buenas noches';
  return <>
    <section className="hero-row">
      <div>
        <div className="eyebrow"><span className="status-dot"/> {todayLabel()}</div>
        <h1>{greeting}, <span>{state.profile.name.split(' ')[0]}</span>.</h1>
        <p>NEXORA convierte todo lo que tienes en la cabeza en un día posible, ordenado y accionable.</p>
      </div>
      <div className="hero-actions"><button className="secondary-btn" onClick={organizeDay}><Sparkles size={16}/> Organizar mi día</button><button className="primary-btn" onClick={() => setModal('task')}><Plus size={18}/> Añadir pendiente</button></div>
    </section>

    <section className="bento hero-bento">
      <motion.div whileHover={{ y: -3 }} className="card focus-card">
        <div className="card-top"><div><p className="label">NEXORA DAILY FLOW</p><h2>Tu día está <span>{taskProgress}%</span> encaminado.</h2></div><div className="icon-glow"><Gauge size={20}/></div></div>
        <div className="progress-bar"><span style={{ width: '78%' }}/></div>
        <div className="micro-stats"><span><CheckCircle2 size={14}/> {state.tasks.filter(t=>t.done).length} completadas</span><span><Sparkles size={14}/> {state.dailyPlan?.focus || 'Organiza tu siguiente movimiento'}</span></div>
      </motion.div>
      <motion.div whileHover={{ y: -3 }} className="card mini-stat-card">
        <p className="label">BALANCE DISPONIBLE</p><div className="money-value">{currency(state.finance.balance)}</div><div className="trend positive"><TrendingUp size={14}/> +12,4% <span>vs. mes pasado</span></div>
      </motion.div>
      <motion.div whileHover={{ y: -3 }} className="card mini-stat-card purple">
        <p className="label">ENFOQUE ESTA SEMANA</p><div className="money-value">5h 10m</div><div className="trend"><Clock3 size={14}/> 8 sesiones <span>completadas</span></div>
      </motion.div>
    </section>

    <section className="content-grid">
      <div className="stack">
        <div className="section-heading"><div><p className="label">PLAN INTELIGENTE</p><h3>Lo que toca ahora</h3></div><button className="ghost-btn" onClick={() => navigate('tasks')}>Ver todo <ArrowRight size={15}/></button></div>
        <div className="card task-card">
          {state.tasks.slice(0,4).map((task, i) => <TaskRow key={task.id} task={task} onToggle={() => toggleTask(task.id)} />)}
        </div>
      </div>
      <div className="stack">
        <div className="section-heading"><div><p className="label">VECTOR</p><h3>Tus metas</h3></div><button className="ghost-btn" onClick={() => navigate('goals')}>Explorar <ArrowRight size={15}/></button></div>
        <div className="card goals-card">
          {state.goals.slice(0,3).map(goal => <GoalRow key={goal.id} goal={goal} />)}
          <div className="goal-total"><div><span>Progreso global</span><strong>{Math.round(state.goals.reduce((a,g)=>a+g.progress,0) / Math.max(state.goals.length,1))}%</strong></div><div className="progress-bar thin"><span style={{ width: `${Math.round(state.goals.reduce((a,g)=>a+g.progress,0) / Math.max(state.goals.length,1))}%` }}/></div></div>
        </div>
      </div>
    </section>

    <section className="content-grid lower">
      <div className="card panel-chart">
        <div className="panel-heading"><div><p className="label">DINERO</p><h3>Ritmo de gastos</h3></div><span className="pill"><Activity size={13}/> Últimos 7 días</span></div>
        <Sparkline values={state.finance.expensesHistory} />
        <div className="chart-foot"><div><span>Total</span><strong>{currency(state.finance.expensesHistory.reduce((a,b)=>a+b,0))}</strong></div><div><span>Promedio diario</span><strong>{currency(Math.round(state.finance.expensesHistory.reduce((a,b)=>a+b,0)/7))}</strong></div></div>
      </div>
      <div className="card daily-card">
        <div className="panel-heading"><div><p className="label">RADAR</p><h3>Estado de hoy</h3></div><Compass size={19}/></div>
        <div className="rings">
          <Ring value={taskProgress} label="Tareas" icon={ListTodo}/>
          <Ring value={81} label="Estudio" icon={BookOpen} tone="cyan"/>
          <Ring value={72} label="Hábitos" icon={Flame} tone="amber"/>
        </div>
      </div>
    </section>
  </>;
}

function TaskRow({ task, onToggle }) {
  return <motion.div layout className={`task-row ${task.done ? 'done' : ''}`}>
    <button className={`check ${task.done ? 'checked' : ''}`} onClick={onToggle}>{task.done && <Check size={14}/>}</button>
    <div className="task-main"><strong>{task.title}</strong><span>{task.category} · {task.due}{task.scheduled ? ` · ${task.scheduled}` : ''}{task.minutes ? ` · ${task.minutes} min` : ''}</span></div>
    <span className={`priority ${task.priority}`}>{task.priority === 'high' ? 'Alta' : task.priority === 'medium' ? 'Media' : 'Baja'}</span>
  </motion.div>;
}

function GoalRow({ goal }) {
  return <div className="goal-row"><div className={`goal-icon ${goal.color}`}><Goal size={16}/></div><div className="goal-main"><div><strong>{goal.title}</strong><span>{goal.subtitle}</span></div><b>{goal.progress}%</b><div className="progress-bar thin"><span style={{width:`${goal.progress}%`}}/></div></div></div>;
}

function Goals({ state, setState, setModal }) {
  const increment = (id) => setState(s => ({ ...s, goals: s.goals.map(g => g.id===id ? {...g, progress: Math.min(100,g.progress+5)} : g) }));
  return <>
    <section className="hero-row"><div><div className="eyebrow"><Target size={14}/> VECTOR DE VIDA</div><h1>Tu dirección, <span>visualizada.</span></h1><p>Las metas se vuelven reales cuando cada pequeño movimiento cuenta.</p></div><button className="primary-btn" onClick={()=>setModal('goal')}><Plus size={18}/> Nueva meta</button></section>
    <div className="goal-wall">{state.goals.map(goal => <motion.div whileHover={{y:-5}} className="card big-goal" key={goal.id}><div className={`big-goal-glow ${goal.color}`}/><div className="big-goal-top"><div className={`goal-icon ${goal.color}`}><Goal size={20}/></div><span className="pill">{goal.subtitle}</span></div><h3>{goal.title}</h3><div className="big-progress"><div><span>Progreso</span><strong>{goal.progress}%</strong></div><div className="progress-bar"><span style={{width:`${goal.progress}%`}}/></div></div><button className="secondary-btn" onClick={()=>increment(goal.id)}><Zap size={15}/> +5% de avance</button></motion.div>)}</div>
  </>;
}

function Tasks({ state, toggleTask, addTask }) {
  const [filter, setFilter] = useState('Todas');
  const list = state.tasks.filter(t => filter==='Todas' ? true : filter==='Pendientes' ? !t.done : t.done);
  return <>
    <section className="hero-row"><div><div className="eyebrow"><ListTodo size={14}/> FLUJO DE TAREAS</div><h1>Menos listas. <span>Más acción.</span></h1><p>Tu sistema convierte intención en próximos pasos.</p></div><button className="primary-btn" onClick={()=>document.getElementById('task-input')?.focus()}><Plus size={18}/> Crear tarea</button></section>
    <div className="inline-add card"><Plus size={18}/><input id="task-input" placeholder="Escribe un nuevo movimiento y presiona Enter…" onKeyDown={e=>{if(e.key==='Enter'){addTask(e.currentTarget.value);e.currentTarget.value=''}}}/></div>
    <div className="tabs"><button className={filter==='Todas'?'active':''} onClick={()=>setFilter('Todas')}>Todas</button><button className={filter==='Pendientes'?'active':''} onClick={()=>setFilter('Pendientes')}>Pendientes</button><button className={filter==='Completadas'?'active':''} onClick={()=>setFilter('Completadas')}>Completadas</button></div>
    <div className="card task-card big-list">{list.map(task=><TaskRow task={task} key={task.id} onToggle={()=>toggleTask(task.id)}/>)}{!list.length&&<Empty icon={CheckCircle2} text="No hay movimientos en este filtro."/>}</div>
  </>;
}

function Study({ state, setToast }) {
  const [subject, setSubject] = useState('Cálculo');
  const add = () => setToast(`Sesión de ${subject} registrada. +25 minutos a tu racha.`);
  return <>
    <section className="hero-row"><div><div className="eyebrow"><BookOpen size={14}/> MODO ESTUDIO</div><h1>Aprender con <span>intención.</span></h1><p>{state.study.streak} días consecutivos construyendo tu próxima versión.</p></div><button className="primary-btn" onClick={add}><Play size={17}/> Registrar sesión</button></section>
    <div className="study-grid"><div className="card streak-card"><div className="streak-orb"><Flame size={27}/></div><p className="label">RACHA ACTUAL</p><strong>{state.study.streak} días</strong><span>Tu mejor racha: 18 días</span></div><div className="card stat-dark"><p className="label">ESTA SEMANA</p><strong>{Math.floor(state.study.weeklyMinutes/60)}h {state.study.weeklyMinutes%60}m</strong><span>+18% vs. semana anterior</span></div><div className="card stat-dark"><p className="label">SESIÓN PROMEDIO</p><strong>38 min</strong><span>Ideal para mantener foco</span></div></div>
    <div className="content-grid"><div className="card panel-chart"><div className="panel-heading"><div><p className="label">MATERIAS</p><h3>Dominio por área</h3></div><select value={subject} onChange={e=>setSubject(e.target.value)}><option>Cálculo</option><option>Programación</option><option>Bases de datos</option></select></div>{state.study.subjects.map(s=><div className="subject-line" key={s.name}><div className="subject-head"><span>{s.name}</span><b>{s.value}%</b></div><div className="progress-bar"><span style={{width:`${s.value}%`}}/></div><small>{s.sessions} sesiones</small></div>)}</div><div className="card study-map"><p className="label">SIGUIENTE SESIÓN</p><h3>25 minutos de {subject}</h3><p>Un bloque corto y preciso para avanzar sin quemarte.</p><div className="focus-preview"><div className="pulse-ring"><Focus size={24}/></div><strong>25:00</strong><span>Modo concentración</span></div><button className="secondary-btn full" onClick={()=>setToast(`Temporizador iniciado para ${subject}.`)}><Play size={15}/> Empezar ahora</button></div></div>
  </>;
}

function Money({ state }) {
  return <>
    <section className="hero-row"><div><div className="eyebrow"><Wallet size={14}/> SISTEMA FINANCIERO</div><h1>Tu dinero, <span>sin niebla.</span></h1><p>Ve el flujo, entiende el ritmo y decide con datos.</p></div><div className="pill big-pill"><CircleDollarSign size={15}/> COP · Colombia</div></section>
    <div className="finance-grid"><div className="card balance-card"><p className="label">BALANCE TOTAL</p><strong>{currency(state.finance.balance)}</strong><div className="trend positive"><TrendingUp size={14}/> 12,4% <span>este mes</span></div><div className="finance-split"><div><span>Ingresos</span><b>{currency(state.finance.income)}</b></div><div><span>Gastos</span><b>{currency(state.finance.expenses)}</b></div></div></div><div className="card finance-chart"><div className="panel-heading"><div><p className="label">GASTOS</p><h3>Últimos 7 días</h3></div><BarChart3 size={18}/></div><Sparkline values={state.finance.expensesHistory}/></div></div>
    <div className="content-grid"><div className="card"><div className="panel-heading"><div><p className="label">DISTRIBUCIÓN</p><h3>¿Dónde se fue?</h3></div></div><div className="expense-row"><span className="dot violet"/> Comida <b>32%</b></div><div className="expense-row"><span className="dot cyan"/> Transporte <b>24%</b></div><div className="expense-row"><span className="dot amber"/> Educación <b>18%</b></div><div className="expense-row"><span className="dot pink"/> Otros <b>26%</b></div></div><div className="card money-note"><Sparkles size={18}/><p className="label">INSIGHT</p><h3>Tu gasto diario promedio es {currency(Math.round(state.finance.expenses/30))}.</h3><p>Usa esta referencia para ajustar tu presupuesto semanal sin perder visibilidad.</p></div></div>
  </>;
}

function FocusPage({ setToast }) {
  const [seconds, setSeconds] = useState(25*60);
  const [running, setRunning] = useState(false);
  useEffect(()=>{ if(!running) return; const id=setInterval(()=>setSeconds(s=>s>0?s-1:0),1000); return ()=>clearInterval(id); },[running]);
  useEffect(()=>{ if(seconds===0){ setRunning(false); setToast('Sesión completada. Gran movimiento.'); } },[seconds]);
  const mins=String(Math.floor(seconds/60)).padStart(2,'0'); const secs=String(seconds%60).padStart(2,'0');
  const pct=(seconds/(25*60))*100;
  return <>
    <section className="hero-row"><div><div className="eyebrow"><Focus size={14}/> NEXORA FOCUS</div><h1>Desconecta el ruido. <span>Entra.</span></h1><p>Un bloque. Una intención. Ninguna excusa.</p></div><div className="pill big-pill"><Activity size={14}/> Deep work mode</div></section>
    <div className="focus-layout"><div className="card focus-timer"><div className="timer-ring" style={{'--p':`${pct}%`}}><div className="timer-inner"><span>ENFOQUE</span><strong>{mins}:{secs}</strong><small>sesión de 25 min</small></div></div><div className="timer-actions"><button className="secondary-btn" onClick={()=>setSeconds(25*60)}><RotateCcw size={15}/></button><button className="primary-btn round" onClick={()=>setRunning(v=>!v)}>{running?<Pause size={18}/>:<Play size={18}/>}</button><button className="secondary-btn" onClick={()=>setToast('Sesión guardada en tu historial.')}><Save size={15}/></button></div></div><div className="card focus-side"><p className="label">INTENCIÓN ACTUAL</p><h3>Terminar un bloque importante antes de revisar notificaciones.</h3><div className="focus-list"><div><Check size={14}/> Una sola tarea</div><div><Check size={14}/> Teléfono lejos</div><div><Check size={14}/> 25 minutos sin interrupciones</div></div><div className="focus-quote"><Sparkles size={15}/><span>“El progreso ama la consistencia.”</span></div></div></div>
  </>;
}

function Circle({ state, setState, setToast }) {
  const [name, setName] = useState('');
  const add = ()=>{if(!name.trim())return; setState(s=>({...s,circle:[...s.circle,{id:Date.now(),name,tag:'Nuevo',note:'Añadido al círculo',online:false}]}));setName('');setToast('Persona añadida a tu círculo.');};
  return <>
    <section className="hero-row"><div><div className="eyebrow"><Heart size={14}/> CÍRCULO</div><h1>Las personas también <span>importan.</span></h1><p>Un lugar tranquilo para recordar lo que conecta contigo.</p></div></section>
    <div className="inline-add card"><Plus size={18}/><input value={name} onChange={e=>setName(e.target.value)} onKeyDown={e=>e.key==='Enter'&&add()} placeholder="Añadir persona y presiona Enter…"/></div>
    <div className="circle-grid">{state.circle.map(person=><motion.div whileHover={{y:-4}} key={person.id} className="card person-card"><div className="person-avatar">{person.name.slice(0,2).toUpperCase()}<span className={person.online?'online':''}/></div><div><h3>{person.name}</h3><span className="pill">{person.tag}</span></div><p>{person.note}</p><button className="ghost-btn" onClick={()=>setToast(`Recordatorio de ${person.name} listo para organizar.`)}>Crear recordatorio <ArrowRight size={14}/></button></motion.div>)}</div>
  </>;
}

function SettingsPage({ state, setState, updateName, setToast }) {
  const reset=()=>{localStorage.removeItem(STORAGE_KEY); setState(defaultState); setToast('NEXORA volvió a su estado inicial.');};
  return <>
    <section className="hero-row"><div><div className="eyebrow"><Settings size={14}/> SISTEMA</div><h1>Hazlo <span>tuyo.</span></h1><p>Personaliza NEXORA para que se sienta como tu espacio.</p></div></section>
    <div className="settings-grid"><div className="card"><div className="panel-heading"><div><p className="label">PERFIL</p><h3>Identidad</h3></div><UserCircle2 size={18}/></div><label>Nombre visible</label><input className="form-input" value={state.profile.name} onChange={e=>updateName(e.target.value)}/><label>Email</label><input className="form-input" value={state.profile.email} disabled/><button className="secondary-btn" onClick={()=>setToast('Cambios guardados automáticamente.') }><Save size={15}/> Guardar</button></div><div className="card"><div className="panel-heading"><div><p className="label">APARIENCIA</p><h3>Atmósfera</h3></div><Moon size={18}/></div><div className="theme-choice"><button className={state.theme==='dark'?'selected':''} onClick={()=>setState(s=>({...s,theme:'dark'}))}><Moon size={17}/> Oscuro</button><button className={state.theme==='light'?'selected':''} onClick={()=>setState(s=>({...s,theme:'light'}))}><Sun size={17}/> Claro</button></div><div className="security-note"><Lock size={15}/><span>Tus datos de demo viven localmente en este navegador.</span></div><button className="danger-btn" onClick={reset}><RotateCcw size={15}/> Restablecer demo</button></div></div>
  </>;
}

function Modal({ type, onClose, onAddTask, onAddGoal }) {
  const [title, setTitle] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const isTask = type==='task';
  return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><motion.div initial={{opacity:0,scale:.96,y:15}} animate={{opacity:1,scale:1,y:0}} exit={{opacity:0,scale:.96,y:15}} className="modal card"><button className="modal-close" onClick={onClose}><X size={18}/></button><div className="icon-glow large"><Sparkles size={20}/></div><p className="label">NUEVO MOVIMIENTO</p><h2>{isTask?'Crear una tarea':'Diseñar una nueva meta'}</h2><p>{isTask?'NEXORA la incorporará a tu flujo de hoy.':'Empieza con una intención; el progreso llegará después.'}</p><input autoFocus className="form-input" value={title} onChange={e=>setTitle(e.target.value)} placeholder={isTask?'Ej. Terminar presentación…':'Ej. Lanzar mi portfolio…'}/>{!isTask&&<input className="form-input" value={subtitle} onChange={e=>setSubtitle(e.target.value)} placeholder="Área · trabajo, estudio, dinero…"/>}<button className="primary-btn full" onClick={()=>isTask?onAddTask(title):onAddGoal(title,subtitle)}><Plus size={17}/> {isTask?'Añadir tarea':'Añadir meta'}</button></motion.div></div>;
}

function Assistant({ onClose, addTask, navigate, setToast, organizeDay }) {
  const [messages, setMessages] = useState([{ role:'ai', text:'Hola. Soy NEXORA AI. Cuéntame todo lo que tienes pendiente, incluso si está desordenado. Yo te ayudo a convertirlo en un plan diario realista.' }]);
  const [input, setInput] = useState('');
  const respond = (value) => {
    const text = value.trim(); if(!text) return;
    const lower = text.toLowerCase();
    let answer = 'Puedo ayudarte a ordenar prioridades, dividir tareas grandes, reservar bloques de tiempo y dejar espacio para descansar.';
    if(lower.includes('organiza') || lower.includes('ordena') || lower.includes('día') || lower.includes('todo lo que tengo')) {
      organizeDay();
      answer = 'Listo. Organicé tus pendientes por prioridad y tiempo estimado. Revisa el Plan Inteligente: lo importante va primero y el resto queda distribuido para que el día sea alcanzable.';
    } else if(lower.includes('estudi') || lower.includes('parcial') || lower.includes('examen')) {
      answer = 'Para estudiar sin saturarte, divide el tema en bloques de 25–45 minutos. Puedo ayudarte a convertir cada bloque en una tarea concreta.';
      navigate('study');
    } else if(lower.includes('debo') || lower.includes('tengo que') || lower.includes('pendiente')) {
      addTask(text, 'NEXORA AI');
      answer = 'Lo convertí en un pendiente de hoy. Después puedo ayudarte a dividirlo en pasos y asignarle un tiempo.';
    } else if(lower.includes('dinero') || lower.includes('gasto') || lower.includes('ahorr')) {
      answer = 'Puedo tener en cuenta tus restricciones de tiempo y dinero cuando reorganizamos el día. También puedes revisar el módulo Dinero.';
      navigate('money');
    }
    setMessages([...messages, {role:'user',text}, {role:'ai',text:answer}]);
    setInput('');
  };
  return <div className="assistant-layer"><motion.aside initial={{x:450}} animate={{x:0}} exit={{x:450}} className="assistant-panel"><div className="assistant-head"><div className="ai-orb"><Sparkles size={18}/></div><div><strong>NEXORA AI</strong><span>Tu organizador personal</span></div><button className="icon-btn" onClick={onClose}><X size={18}/></button></div><div className="assistant-chips"><button onClick={()=>respond('Organiza mi día')}>Organizar mi día</button><button onClick={()=>respond('Tengo muchas cosas pendientes')}>Tengo demasiadas cosas</button><button onClick={()=>navigate('focus')}>Necesito concentrarme</button></div><div className="assistant-messages">{messages.map((m,i)=><div className={`msg ${m.role}`} key={i}><div className="msg-dot">{m.role==='ai'?<Sparkles size={12}/>:<UserCircle2 size={12}/>}</div><p>{m.text}</p></div>)}</div><form className="assistant-input" onSubmit={e=>{e.preventDefault();respond(input)}}><input value={input} onChange={e=>setInput(e.target.value)} placeholder="Cuéntame qué tienes que hacer…"/><button type="submit"><ArrowRight size={18}/></button></form></motion.aside></div>;
}

function Toast({ text }) { return <motion.div initial={{y:40,opacity:0}} animate={{y:0,opacity:1}} exit={{y:40,opacity:0}} className="toast"><CheckCircle2 size={17}/>{text}</motion.div>; }
function Empty({icon:Icon,text}) { return <div className="empty"><Icon size={30}/><p>{text}</p></div>; }

createRoot(document.getElementById('root')).render(<App />);
