import React from "react";
import StatementUpload from "./StatementUpload";
import { useNavigate } from "react-router-dom";
import { supabase } from "./supabaseClient";

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
        <button onClick={handleLogout} style={{ marginLeft: "auto", padding: "8px 16px", cursor: "pointer" }}>
          Logout
        </button>
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
