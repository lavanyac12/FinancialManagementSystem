import React, { useState, useEffect } from "react";
import axios from "axios";
import { supabase } from "./supabaseClient";

export default function SmartGoalsButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="upload-btn" onClick={() => setOpen(true)}>
        Smart Goals
      </button>
      {open && <SmartGoalsModal onClose={() => setOpen(false)} />}
    </>
  );
}


function SmartGoalsModal({ onClose }) {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", target_amount: "", income_allocation: "" });
  const [saving, setSaving] = useState(false);
  // Default to backend on port 8000 (matches local uvicorn), allow override via env
  const API_ROOT = process.env.REACT_APP_API_URL || `http://${window.location.hostname}:8000`;
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchGoals();
  }, []);

  async function fetchGoals() {
    setLoading(true);
    try {
      const res = await axios.get(`${API_ROOT}/smart-goals`);
      setGoals(res.data.goals || []);
      setError(null);
    } catch (err) {
      console.error("fetchGoals error", err);
      setError(err?.response?.data?.error || err?.message || "Failed to load goals");
      setGoals([]);
    }
    setLoading(false);
  }

  function openCreate() {
    setEditing(null);
    setForm({ name: "", target_amount: "", income_allocation: "" });
    setShowForm(true);
  }

  function openEdit(goal) {
    setEditing(goal);
    setForm({ name: goal.name || "", target_amount: goal.target_amount || "", income_allocation: goal.income_allocation || "" });
    setShowForm(true);
  }

  function validate() {
    if (!form.name || form.name.length > 50) return "name required (max 50 chars)";
    const ta = parseFloat(form.target_amount);
    if (Number.isNaN(ta) || ta <= 1) return "target_amount must be > 1";
    const ia = parseFloat(form.income_allocation);
    if (Number.isNaN(ia) || ia < 0 || ia > 99) return "income_allocation must be 0-99";
    return null;
  }

  async function submitForm(e) {
    e.preventDefault();
    const err = validate();
    if (err) return alert(err);
    setSaving(true);
    // build payload with numeric conversions so backend validators receive numbers
    const payload = {
      name: String(form.name || "").trim(),
      target_amount: Number.parseFloat(form.target_amount),
      income_allocation: Number.parseFloat(form.income_allocation),
    };
    try {
      let res;
      if (editing) {
        res = await axios.put(`${API_ROOT}/smart-goals/${editing.goal_id}`, payload);
      } else {
        res = await axios.post(`${API_ROOT}/smart-goals`, payload);
      }
      // handle server-side reported errors (some endpoints return 200 with { error: '...' })
      if (res && res.data && res.data.error) {
        throw new Error(res.data.error || JSON.stringify(res.data));
      }
      setShowForm(false);
      setError(null);
      fetchGoals();
    } catch (e) {
      console.error("Save error:", e);
      // try to extract useful message from axios error
      let msg = "Save failed";
      if (e.response && e.response.data) {
        const d = e.response.data;
        msg = d.error || d.message || JSON.stringify(d);
      } else if (e.message) {
        msg = e.message;
      }
      setError(msg);
      alert(msg);
    } finally {
      setSaving(false);
    }
  }

  async function deleteGoal() {
    if (!editing || !editing.goal_id) return;
    if (!window.confirm(`Delete goal "${editing.name}"?`)) return;
    setSaving(true);
    try {
      const res = await axios.delete(`${API_ROOT}/smart-goals/${editing.goal_id}`);
      if (res && res.data && res.data.error) {
        throw new Error(res.data.error || JSON.stringify(res.data));
      }
      setShowForm(false);
      setError(null);
      fetchGoals();
    } catch (e) {
      console.error("Delete error:", e);
      let msg = "Delete failed";
      if (e.response && e.response.data) {
        const d = e.response.data;
        msg = d.error || d.message || JSON.stringify(d);
      } else if (e.message) {
        msg = e.message;
      }
      setError(msg);
      alert(msg);
    } finally {
      setSaving(false);
    }
  }

  async function deleteGoal() {
    if (!editing || !editing.goal_id) return;
    if (!window.confirm(`Delete goal "${editing.name}"?`)) return;
    setSaving(true);
    try {
      const res = await axios.delete(`${API_ROOT}/smart-goals/${editing.goal_id}`);
      if (res && res.data && res.data.error) {
        throw new Error(res.data.error || JSON.stringify(res.data));
      }
      setShowForm(false);
      setError(null);
      fetchGoals();
    } catch (e) {
      console.error("Delete error:", e);
      let msg = "Delete failed";
      if (e.response && e.response.data) {
        const d = e.response.data;
        msg = d.error || d.message || JSON.stringify(d);
      } else if (e.message) {
        msg = e.message;
      }
      setError(msg);
      alert(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={modalOverlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <div style={modalHeaderStyle}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>Smart Goals</div>
          <button className="upload-btn" onClick={onClose}>Close</button>
        </div>

        <div style={{ marginTop: 12, padding: "12px 18px" }}>
          {error && (
            <div style={{ color: "#b00020", marginBottom: 8 }}>
              <strong>Error:</strong> {String(error)}
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ marginLeft: 8, fontSize: 20, fontWeight: 700 }}>{goals.length} goal(s)</div>
            <div>
              <button className="upload-btn" onClick={openCreate} style={{ marginLeft: 1}}>Add Smart Goal</button>
            </div>
          </div>

          {loading ? (
            <div>Loading...</div>
          ) : (
            <ul style={{ marginTop: 12, listStyle: 'none', padding: 0 }}>
              {goals.map((g) => (
                <li key={g.goal_id} style={{ marginBottom: 18, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
                    <div style={{ fontSize: 20, fontWeight: 700, marginLeft: 8 }}>{g.name}</div>
                    <div style={{ fontSize: 14, marginLeft: 8, lineHeight: '1.5', color: '#e6eef6' }}>
                      <div>Target Amount: {g.target_amount}</div>
                      <div>Allocation: {g.income_allocation}%</div>
                      <div>Amount Saved: {g.amount_saved ?? g.AmountSaved ?? 0}</div>
                    </div>
                  </div>
                  <div style={{ marginLeft: 12 }}>
                    <button className="upload-btn" onClick={() => openEdit(g)} style={{ marginLeft: 12 }}>Edit</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {showForm && (
          <form onSubmit={submitForm} style={{ marginTop: 12 }}>
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: "block", fontWeight: 600, fontSize: 20, marginLeft: 15, marginBottom: 6 }}>Name</label>
              <input
                placeholder="Enter goal name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                maxLength={50}
                required
                style={{ width: "90%", padding: "8px", background: '#fff', color: '#000', borderRadius: 4, marginLeft: 15 }}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: "block", fontWeight: 600, fontSize: 20, marginLeft: 15, marginBottom: 6, marginLeft: 15, marginTop: 20  }}>Target Amount</label>
              <input
                placeholder="e.g. 1500.00"
                value={form.target_amount}
                onChange={(e) => setForm({ ...form, target_amount: e.target.value })}
                type="number"
                step="0.01"
                min="1.01"
                required
                style={{ width: "90%", padding: "8px", background: '#fff', color: '#000', borderRadius: 4, marginLeft: 15 }}
              />
            </div>
            <div style={{ marginBottom: 8}}>
              <label style={{ display: "block", fontWeight: 700, fontSize: 20, marginLeft: 15, marginBottom: 6, marginTop: 20  }}>Income Allocation (%)</label>
              <input
                placeholder="0 - 99"
                value={form.income_allocation}
                onChange={(e) => setForm({ ...form, income_allocation: e.target.value })}
                type="number"
                step="0.01"
                min="0"
                max="99"
                required
                style={{ width: "90%", padding: "8px", background: '#fff', color: '#000', borderRadius: 4, marginLeft: 15 }}
              />
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 23, marginLeft: 15 }}>
              <button className="upload-btn" type="submit" style={{ marginBottom: 20}} disabled={saving}>{saving ? "Saving..." : "Save"}</button>
              <button className="upload-btn" type="button" onClick={() => setShowForm(false)} style={{ marginBottom: 20}}>Cancel</button>
              {editing && (
                <button className="upload-btn" type="button" onClick={deleteGoal} disabled={saving} style={{ background: '#b03e49ff', marginBottom: 20}}>
                  Delete
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

const modalOverlayStyle = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  background: "rgba(0,0,0,0.4)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 2000,
};

const modalStyle = {
  background: "#232e3c",
  color: "#fff",
  padding: 0,
  borderRadius: 8,
  width: "600px",
  maxHeight: "80vh",
  overflowY: "auto",
  boxShadow: "0 12px 40px rgba(0,0,0,0.5)",
  border: "1px solid rgba(255,255,255,0.06)",
};

const modalHeaderStyle = {
  height: 72,
  padding: "0 20px",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  borderBottom: "1px solid rgba(255,255,255,0.06)",
};
