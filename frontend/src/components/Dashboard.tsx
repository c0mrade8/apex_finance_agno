import { useEffect, useState } from "react";
import { getAlerts, getLogs, getWorkflow, runOrchestrator } from "../api/api";
import { type Alert, type Log, type Workflow } from "../types/types";
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const COMPANIES = [
  "techforge_saas", "precisionmfg_inc", "retailco", "healthservices_plus",
  "logisticspro", "industrialsupply_co", "dataanalytics_corp", "ecopackaging_ltd"
];

export default function Dashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [workflow, setWorkflow] = useState<Workflow[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleTimeString());

  const loadData = async () => {
    try {
      const [a, l, w] = await Promise.all([
        getAlerts(),
        getLogs(),
        getWorkflow()
      ]);

      // --- LOGIC FIX: Normalization to ensure UI "sees" the data ---
      const normalizedAlerts = (a.data || a || []).map((item: any) => ({
        company: item.company || item.company_id || "SYSTEM",
        message: item.message,
        severity: item.severity || "INFO"
      }));

      const normalizedLogs = (l.data || l || []).map((item: any) => ({
        agent_name: item.agent_name || item.agent || "SYS",
        message: item.message,
      }));

      const normalizedWorkflow = (w.data || w || []).map((item: any) => ({
        agent: item.agent || item.agent_name,
        company: item.company || item.company_id,
        status: item.status
      }));

      setAlerts(normalizedAlerts);
      setLogs(normalizedLogs);
      setWorkflow(normalizedWorkflow);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (error) {
      console.error("Fetch error:", error);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleRun = async () => {
    setIsProcessing(true);
    try {
      await runOrchestrator("2026-01");
      setTimeout(() => setIsProcessing(false), 5000); // UI feedback delay
    } catch (error) {
      console.error("Run failed:", error);
      setIsProcessing(false);
    }
  };

  const completedSteps = workflow.filter(w => w.status === "COMPLETED").length;
  const progressPercent = workflow.length ? Math.round((completedSteps / workflow.length) * 100) : 0;

  const chartData = [
    { name: "Alerts", value: alerts.length, color: "#f43f5e" },
    { name: "Logs", value: logs.length, color: "#3b82f6" },
    { name: "Progress %", value: progressPercent, color: "#10b981" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white p-8 font-sans selection:bg-blue-500/30">
      
      {/* --- HEADER --- */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-blue-400 tracking-tight">
            APEX FINANCE AI
          </h1>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">
              System Live • {lastUpdated}
            </p>
            <span className="text-slate-800">|</span>
            <p className="text-xs text-slate-400">
              Audit Completion: <span className="text-blue-400 font-bold">{progressPercent}%</span>
            </p>
          </div>
        </div>
        <button
          onClick={handleRun}
          disabled={isProcessing}
          className={`${
            isProcessing ? 'bg-slate-800 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 active:scale-95'
          } text-white px-8 py-3 rounded-xl font-bold transition-all shadow-lg shadow-blue-900/20 border border-blue-400/20`}
        >
          {isProcessing ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              Orchestrating Agents...
            </span>
          ) : "Run Month-End Close"}
        </button>
      </div>

      {/* --- TOP ROW: METRICS & CHART --- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 grid grid-cols-3 gap-4">
            <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 backdrop-blur-sm group hover:border-rose-500/30 transition-colors">
                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Critical Alerts</p>
                <p className="text-5xl font-mono text-rose-500 mt-2">{alerts.length}</p>
            </div>
            <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 backdrop-blur-sm group hover:border-blue-500/30 transition-colors">
                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Process Logs</p>
                <p className="text-5xl font-mono text-blue-500 mt-2">{logs.length}</p>
            </div>
            <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 backdrop-blur-sm group hover:border-emerald-500/30 transition-colors">
                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Workflow Tasks</p>
                <p className="text-5xl font-mono text-emerald-500 mt-2">{workflow.length}</p>
            </div>
        </div>
        
        <div className="bg-slate-900 p-4 rounded-2xl border border-slate-800 h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#475569', fontSize: 10}} />
                    <Tooltip 
                        cursor={{fill: 'rgba(255,255,255,0.05)'}} 
                        contentStyle={{backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '12px'}} 
                    />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={40}>
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
      </div>

      {/* --- DYNAMIC COMPANY HUB --- */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-8">
        {COMPANIES.map((company) => {
          const companyTasks = workflow.filter((w:any) => w.company === company);
          const isDone = companyTasks.length > 0 && companyTasks.every(t => t.status === "COMPLETED");
          const isPending = companyTasks.length > 0 && !isDone;

          return (
            <div key={company} className="bg-slate-900/40 p-3 rounded-xl border border-slate-800 transition-all hover:bg-slate-900/60">
              <p className="text-[10px] text-slate-500 font-bold truncate uppercase tracking-tighter">
                {company.replaceAll('_', ' ')}
              </p>
              <div className="flex items-center gap-1.5 mt-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    isDone ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : 
                    isPending ? "bg-yellow-400 animate-pulse shadow-[0_0_8px_#facc15]" : "bg-slate-700"
                  }`}></span>
                  <span className={`text-[9px] font-black tracking-widest ${
                    isDone ? "text-emerald-400" : 
                    isPending ? "text-yellow-400" : "text-slate-600"
                  }`}>
                    {isDone ? "CLEARED" : isPending ? "ACTIVE" : "IDLE"}
                  </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* --- FEED & LOGS --- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 overflow-hidden">
        
        {/* Intelligence Feed */}
        <div className="lg:col-span-2 bg-slate-900/50 p-6 rounded-2xl border border-slate-800 shadow-2xl flex flex-col h-[500px]">
          <h3 className="text-xl font-bold mb-6 flex items-center gap-3">
            <span className="w-2 h-2 bg-rose-500 rounded-full animate-pulse"></span>
            Intelligence Feed
          </h3>
          <div className="space-y-4 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-800 hover:scrollbar-thumb-slate-700">
            {alerts.length === 0 ? (
              <div className="py-24 text-center border-2 border-dashed border-slate-800/50 rounded-2xl bg-slate-950/30">
                <p className="text-slate-600 italic text-sm">No alerts detected — initiate Month-End Close to begin agent analysis</p>
              </div>
            ) : (
              alerts.map((a, i) => (
                <div key={i} className={`p-4 bg-slate-950 border-l-4 rounded-r-xl transition-transform hover:translate-x-1 ${
                    a.severity === "CRITICAL" ? "border-rose-600" :
                    a.severity === "HIGH" ? "border-yellow-500" : "border-slate-600"
                }`}>
                  <div className="flex justify-between mb-1">
                    <span className={`text-[10px] font-black uppercase tracking-widest ${
                        a.severity === "CRITICAL" ? "text-rose-500" :
                        a.severity === "HIGH" ? "text-yellow-500" : "text-slate-500"
                    }`}>{a.severity}</span>
                    <span className="text-slate-600 text-[10px] font-mono uppercase">{a.company}</span>
                  </div>
                  {/* whitespace-pre-wrap ensures AI paragraphs look clean */}
                  <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">{a.message}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Sidebar Status */}
        <div className="flex flex-col gap-6 h-[500px]">
            <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 flex-1 flex flex-col min-h-0">
                <h3 className="text-xs font-black text-slate-500 mb-4 uppercase tracking-widest flex justify-between">
                    Agent Workflow
                    {workflow.length > 0 && <span className="text-blue-500">{progressPercent}%</span>}
                </h3>
                <div className="space-y-2 overflow-y-auto scrollbar-hide">
                    {workflow.length === 0 ? (
                       <p className="text-[11px] text-slate-700 italic py-4">Run orchestrator to deploy agents...</p>
                    ) : (
                      workflow.map((w, i) => (
                          <div key={i} className="flex justify-between items-center bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/50">
                              <span className="text-[11px] text-slate-300 font-medium">{w.agent || 'Agent'}</span>
                              <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${
                                  w.status === 'COMPLETED' ? 'text-emerald-400 bg-emerald-500/10' : 
                                  w.status === 'FAILED' ? 'text-rose-500 bg-rose-500/10' : 'text-yellow-400 bg-yellow-500/10'
                              }`}>{w.status}</span>
                          </div>
                      ))
                    )}
                </div>
            </div>

            <div className="bg-slate-900 p-6 rounded-2xl border border-slate-800 flex-1 flex flex-col min-h-0">
                <h3 className="text-xs font-black text-slate-500 mb-4 uppercase tracking-widest">Audit Logs</h3>
                <div className="space-y-2 overflow-y-auto font-mono text-[10px] scrollbar-thin scrollbar-thumb-slate-800">
                    {logs.length === 0 ? (
                        <p className="text-[10px] text-slate-700 italic">Logs will appear on execution...</p>
                    ) : (
                      logs.slice(0, 50).reverse().map((log, i) => (
                          <div key={i} className="text-slate-500 border-b border-slate-800/30 pb-1.5 flex gap-2">
                              <span className="text-blue-600 font-bold shrink-0">[{log.agent_name}]</span>
                              <span className="truncate text-slate-400">{log.message}</span>
                          </div>
                      ))
                    )}
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}