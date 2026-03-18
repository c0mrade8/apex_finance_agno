import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000";

// ✅ Extract .data immediately so the component gets a clean array
export const getAlerts = () => axios.get(`${BASE_URL}/alerts/`).then(res => res.data);
export const getLogs = () => axios.get(`${BASE_URL}/logs/`).then(res => res.data);
export const getWorkflow = () => axios.get(`${BASE_URL}/workflow/`).then(res => res.data);

export const runOrchestrator = (period: string) =>
  axios.post(`${BASE_URL}/orchestrator/run?period=${period}`).then(res => res.data);