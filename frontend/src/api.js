const API_BASE = '/api/v1';

export const api = {
  async checkHealth() {
    try {
      const res = await fetch('/health');
      return res.ok;
    } catch {
      return false;
    }
  },

  async getPersons() {
    const res = await fetch(`${API_BASE}/persons`);
    if (!res.ok) throw new Error('Failed to fetch registered persons');
    return res.json();
  },

  async getPerson(personId) {
    const res = await fetch(`${API_BASE}/persons/${personId}`);
    if (!res.ok) throw new Error('Failed to fetch person details');
    return res.json();
  },

  async createPerson(payload) {
    const res = await fetch(`${API_BASE}/persons`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to register person');
    }
    return res.json();
  },

  async startResearch(personId) {
    const res = await fetch(`${API_BASE}/research/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ person_id: personId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to trigger research job');
    }
    return res.json();
  },

  async getResearchStatus(jobId) {
    const res = await fetch(`${API_BASE}/research/${jobId}`);
    if (!res.ok) throw new Error('Failed to poll research progress');
    return res.json();
  },

  async getAppearances(personId, status = null) {
    const url = status
      ? `${API_BASE}/persons/${personId}/appearances?identity_status=${status}`
      : `${API_BASE}/persons/${personId}/appearances`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch appearances');
    return res.json();
  },

  async getTimeline(personId) {
    const res = await fetch(`${API_BASE}/persons/${personId}/timeline`);
    if (!res.ok) throw new Error('Failed to fetch appearance timeline');
    return res.json();
  },

  async getSources(personId) {
    const res = await fetch(`${API_BASE}/persons/${personId}/sources`);
    if (!res.ok) throw new Error('Failed to fetch sources');
    return res.json();
  },

  async getReport(personId) {
    const res = await fetch(`${API_BASE}/persons/${personId}/report`);
    if (!res.ok) throw new Error('Failed to fetch intelligence report');
    return res.json();
  },
};

