export type Alert = {
  company: string;
  message: string;
  severity: string;
};

export type Log = {
  id: string;
  agent_name: string;
  agent: string;
  message: string;
  time: string;
};

export type Workflow = {
  agent: string;
  company: string;
  status: string;
};