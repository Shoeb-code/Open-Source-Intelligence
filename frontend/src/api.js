const API_BASE = '/api/v1';

export const api = {
  async checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) return true;
      const fallback = await fetch('/health');
      return fallback.ok;
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

  async deletePerson(personId) {
    const res = await fetch(`${API_BASE}/persons/${personId}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error('Failed to delete person');
    }
    return true;
  },

  async updatePerson(personId, payload) {
    const res = await fetch(`${API_BASE}/persons/${personId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update target details');
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

  async analyzeUrl(personId, { url, source_type = null, title = null }) {
    const res = await fetch(`${API_BASE}/persons/${personId}/analyze-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, source_type, title }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to analyze URL');
    }
    return res.json();
  },

  async deleteAppearance(personId, appearanceId) {
    const res = await fetch(`${API_BASE}/persons/${personId}/appearances/${appearanceId}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error('Failed to delete appearance');
    }
    return true;
  },

  async enrichLinkedInProfile(personId, { force = false, profile_url = null } = {}) {
    const res = await fetch(`${API_BASE}/linkedin/enrich/${personId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force, profile_url }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to enrich LinkedIn profile');
    }
    return res.json();
  },

  async getInsights(personId) {
    const res = await fetch(`${API_BASE}/persons/${personId}/insights`);
    if (!res.ok) throw new Error('Failed to fetch AI insights');
    return res.json();
  },

  async generateInsights(personId, { focus_notes = null } = {}) {
    const res = await fetch(`${API_BASE}/persons/${personId}/generate-insights`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ focus_notes }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to generate AI insights');
    }
    return res.json();
  },
};
