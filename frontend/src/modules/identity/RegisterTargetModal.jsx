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

      setName('');
      setProfession('');
      setBio('');
      setLinkedin('');
      setYoutube('');
      setInstagram('');
      onTargetRegistered(newPerson);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to add person');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-3 sm:p-4">
      <div className="w-full max-w-lg rounded-2xl p-5 sm:p-6 bg-white border border-slate-200 shadow-2xl max-h-[92vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-5">
          <div className="flex items-center gap-2">
            <UserPlus size={20} className="text-blue-600" />
            <h3 className="text-lg font-bold text-slate-900">Add a Person to Research</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 transition-colors p-1 rounded-lg hover:bg-slate-100"
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
          <div>
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Full Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Madhu Lunawat"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Company or Role
            </label>
            <input
              type="text"
              placeholder="e.g. Founder at The Wealth Company"
              value={profession}
              onChange={(e) => setProfession(e.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Short Bio / Notes
            </label>
            <textarea
              rows={2}
              placeholder="Optional background notes..."
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              className="input-field resize-y"
            />
          </div>

          <div className="border-t border-slate-200 pt-3">
            <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider mb-2">
              Social Links (Optional)
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

          <div className="flex justify-end gap-3 mt-4 pt-3 border-t border-slate-200">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? 'Adding...' : 'Add Person'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
