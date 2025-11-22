import React from "react";
import "./App.css";
import StatementUpload from "./StatementUpload";

function App() {
  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <span>Finance Management</span>
      </header>

      {/* Dashboard */}
      <div className="dashboard">
        <StatementUpload />
      </div>
    </div>
  );
}

export default App;
