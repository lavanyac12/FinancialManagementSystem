import React, { useState, useEffect } from "react";
import StatementUpload from "./StatementUpload";
import { useNavigate } from "react-router-dom";
import { supabase } from "./supabaseClient";
import SmartGoalsButton from "./SmartGoals";

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
        <h2>Upload Statement</h2>
        <StatementUpload />
      </div>
    </div>
  );
}

export default Dashboard;

