import React, { useState } from "react";
import "./App.css";
import StatementUpload from "./StatementUpload";
import Login from "./Login";

function App() {
  const [token, setToken] = useState(localStorage.getItem('supabase_token'));

  const handleLogin = (t) => {
    setToken(t);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <span>Finance Management</span>
      </header>

      {/* Dashboard */}
      <div className="dashboard">
        <Login onLogin={handleLogin} />
        <StatementUpload />
      </div>
    </div>
  );
}

export default App;
