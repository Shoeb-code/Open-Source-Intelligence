import React, { useState } from 'react';
import { UserPlus, X } from 'lucide-react';
import { api } from '../../api';

export default function RegisterTargetModal({ isOpen, onClose, onTargetRegistered }) {
  const [name, setName] = useState('');
  const [profession, setProfession] = useState('');
  const [bio, setBio] = useState('');
  const [linkedin, setLinkedin] = useState('');
  const [youtube, setYoutube] = useState('');
  const [instagram, setInstagram] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const newPerson = await api.createPerson({
        name: name.trim(),
        profession: profession.trim() || null,
        biography: bio.trim() || null,
        linkedin_url: linkedin.trim() || null,
        youtube_url: youtube.trim() || null,
        instagram_url: instagram.trim() || null,
      });

      onTargetRegistered(newPerson);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to register target');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="glass-panel w-full max-w-lg rounded-2xl p-6 bg-slate-900 border border-slate-700/80 shadow-2xl">
        <div className="flex justify-between items-center mb-5">
          <div className="flex items-center gap-2">
            <UserPlus size={20} className="text-cyan-400" />
            <h3 className="text-lg font-bold text-slate-100">Register Target for Intelligence</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Full Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Sundar Pichai"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Profession & Affiliation
            </label>
            <input
              type="text"
              placeholder="e.g. CEO at Alphabet and Google"
              value={profession}
              onChange={(e) => setProfession(e.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Biography / Context
            </label>
            <textarea
              rows={2}
              placeholder="Short professional summary or background..."
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className="input-field resize-y"
            />
          </div>

          <div className="border-t border-slate-800 pt-3">
            <p className="text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-2">
              Known Social & Channel Profiles (Optional)
            </p>

            <div className="flex flex-col gap-2">
              <input
                type="url"
                placeholder="LinkedIn Profile URL"
                value={linkedin}
                onChange={(e) => setLinkedin(e.target.value)}
                className="input-field"
              />
              <input
                type="url"
                placeholder="YouTube Channel URL"
                value={youtube}
                onChange={(e) => setYoutube(e.target.value)}
                className="input-field"
              />
              <input
                type="url"
                placeholder="Instagram Profile URL"
                value={instagram}
                onChange={(e) => setInstagram(e.target.value)}
                className="input-field"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-4 pt-3 border-t border-slate-800">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? 'Registering...' : 'Register Target'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
