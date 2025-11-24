import React, { useState, useEffect } from "react";
import StatementUpload from "./StatementUpload";
import { useNavigate } from "react-router-dom";
import { supabase } from "./supabaseClient";
import SmartGoalsButton from "./SmartGoals";
import ExpensePieChart from "./ExpensePieChart";

function Dashboard() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem("supabase_token");
    navigate("/login");
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <span>Finance Management</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          <SmartGoalsButton />
          <button className="upload-btn" onClick={handleLogout} style={{ cursor: "pointer", marginRight: 50 }}>
            Logout
          </button>
        </div>
      </header>

      {/* Dashboard */}
      <div className="dashboard">
        <div style={{ marginBottom: '40px' }}>
          <h2>Upload Statement</h2>
          <StatementUpload />
        </div>

        <div style={{ marginTop: '40px', background: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <ExpensePieChart />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

